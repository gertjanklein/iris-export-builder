#!/usr/bin/env python3
# encoding: UTF-8

import sys, os
from os.path import dirname, join, isabs, abspath, exists, splitext, isfile, basename
import re
import logging
import urllib.request as urq
import datetime
import http.cookiejar
import json
import base64

from config import get_config, ConfigurationError
from deployment import append_export_notes


def main(cfgfile):
    # Initial logging setup: file next to ini file. Errors parsing the
    # config file will be logged here.
    setup_basic_logging(cfgfile)
    
    # Log unhandled exceptions
    sys.excepthook = unhandled_exception

    # Get configuration and do final logging setup
    config = get_config(cfgfile, setup_logging)
    
    # Setup basic auth handler for IRIS, if we need to convert UDL to XML
    if config.Source.srctype == 'udl':
        setup_urllib(config)

    # Get object representing repo
    repo = get_repo(config)

    # Determine export filename
    export_name = get_export_name(config, repo.name)

    # Create an export file containing all the items
    with open(export_name, 'w', encoding='UTF-8') as outfile:
        count = create_export(config, repo, outfile)
    
    # Give some feedback
    logging.info(f"\nDone; added {count} items to export in {export_name}.\n")
    msgbox(f"Exported {count} items to {export_name}.")

    

def create_export(config, repo, outfile):
    """Create the export from the items in the repo object."""
    is_open = False
    is_udl = config.Source.srctype == 'udl'

    count = 0

    # Write IRIS items to export file. Write the opening Export tag as well.
    for item in repo.src_items:
        if is_udl:
            logging.info(f'Converting {item.name}')
            export = convert_to_xml(config, item)
        else:
            logging.info(f'Adding {item.name}')
            export = item.data
        
        if not is_open:
            # outfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            outfile.write(extract_export_header(export) + '\n')
            is_open = True
        outfile.write(extract_export_content(export) + '\n')
        count += 1
    
    for item in repo.data_items:
        logging.info(f'Adding {item.name}')
        export = item.data
        
        if not is_open:
            # outfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            outfile.write(extract_export_header(export) + '\n')
            is_open = True
        outfile.write(extract_export_content(export) + '\n')
        count += 1
    
    if repo.csp_items:
        if config.CSP.export == 'embed':
            # If this is just CSP files, we must write the Export tag ourselves
            if not is_open:
                outfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                outfile.write('<Export generator="IRIS" version="26">\n')

            # Append the items to the export
            count += append_csp_items(config, repo, outfile)
        else:
            # Create a separate CSP export file
            count += export_csp_separate(config, repo, outfile.name)

    # Append export notes to make export usable as a deployment 
    if config.Local.deployment:
        append_export_notes(config, repo, outfile)

    # Close Export element
    outfile.write('</Export>\n')

    return count


def convert_to_xml(config, item):
    """Convert an IRIS item from UDL to XML format."""

    data = item.data.encode('UTF-8')

    svr = config.Server
    url = f"http://{svr.host}:{svr.port}/api/atelier/v1/{svr.namespace}/cvt/doc/xml"
    rq = urq.Request(url, method='POST', data=data, headers={'Content-Type': 'text/plain; charset=utf-8'})
    
    # Get and convert from JSON
    with urq.urlopen(rq) as rsp:
        data = json.load(rsp)
    # Errors are returned here, not in data['status']['errors']
    status = data['result']['status']
    if status:
        raise ValueError(f'Error converting {item.name} to XML: {status}.')
    content = data['result']['content']

    # Content has \r\n as line ending, but we want the 'internal' \n.
    content = content.replace('\r', '')

    return content


def export_csp_separate(config, repo, export_name):
    """ Creates a separate output file with CSP items. """

    base, ext = splitext(export_name)
    export_name = base+'_csp'+ext

    with open(export_name, 'w', encoding='UTF-8') as outfile:
        outfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        # Version can be relatively old, nothing changed since then
        outfile.write('<Export generator="Cache" version="25">\n')
        count = append_csp_items(config, repo, outfile)
        outfile.write('\n</Export>\n')
    return count


def append_csp_items(config, repo, outfile):
    count = 0
    for item in repo.csp_items:
        name = item.relpath
        split = split_csp(config, name)
        if not split:
            continue
        app, cspname = split
        logging.info(f'Adding {name} as app "{app}", item "{cspname}".')
        count += 1

        # Get CSP item data
        data = item.data
        
        if item.is_text:
            append_csp_text(app, cspname, data, outfile)
        else:
            append_csp_binary(app, cspname, data, outfile)

    return count


def split_csp(config, name:str):
    """ Split CSP item in app and page. """
    
    for i, parser in enumerate(config.CSP.parsers):
        match = re.fullmatch(parser.regex, name)
        if not match:
            if parser.nomatch != 'error':
                logging.debug(f"Item {name} does not match regex in parser {i+1} ('{parser.regex}').")
                continue
            raise ConfigurationError(f"Error: item {name} does not match regex in parser {i+1} ('{parser.regex}').")
        app = parser.app
        for i, v in enumerate(match.groups()):
            if v is not None:
                app = app.replace(f'\\{i+1}', v)
        page = parser.item
        for i, v in enumerate(match.groups()):
            if v is not None:
                page = page.replace(f'\\{i+1}', v)

        # Some basic validity checks:
        if app[0] != '/':
            raise ValueError('Invalid application: must start with a slash')
        if app[-1] == '/':
            raise ValueError('Invalid application: must not end with a slash')
        
        if page[0] == '/':
            raise ValueError('Invalid page: must not start with a slash')
        if page[-1] == '/':
            raise ValueError('Invalid page: must not end with a slash')
        
        return app, page
    
    return None


def append_csp_text(app, name, data, outfile):
    data = data.replace('\r', '')
    outfile.write(f'<CSP name="{name}" application="{app}"><![CDATA[')
    outfile.write(data)
    outfile.write(']]></CSP>\n\n')


def append_csp_binary(app, name, data, outfile):
    outfile.write(f'<CSPBase64 name="{name}" application="{app}"><![CDATA[\n')
    outfile.write(base64.encodebytes(data).decode())
    outfile.write(']]></CSPBase64>\n\n')


def extract_export_header(export):
    """Extract XML declaration and <Export> element"""
    result = []
    for line in export.splitlines(True):
        result.append(line)
        if line.startswith('<Export'): break
    
    return ''.join(result)
        
    
def extract_export_content(export):
    """Extract contents of <Export> element"""
    
    # We use the knowledge that the XML declaration and Export start and
    # end tag are always on a line of their own, so we can use simple
    # string processing to get the content.

    result = []
    for line in export.splitlines(True):
        if line.startswith('<?xml'): continue
        if line.startswith('<Export'): continue
        if line.startswith('</Export'): continue
        result.append(line)
    content = ''.join(result)

    return content


def get_export_name(config, repo_name):
    """ Determines the output (export) filename."""

    ts = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M')
    cfgname = splitext(basename(config.cfgfile))[0]
    replacements = {
        'name': repo_name,
        'timestamp': ts,
        'cfgname': cfgname }

    name = config.Local.outfile
    try:
        name = name.format(**replacements)
    except KeyError as e:
        logging.warning(f"Warning: ignoring unrecognized replacement in outfile: {e.args[0]}\n")

    # Interpret relative path relative to ini file location
    if not isabs(name):
        name = join(config.cfgdir, name)

    # Make sure the output directory exists
    d = dirname(name)
    if not exists(d):
        os.makedirs(d, exist_ok=True)
    
    return name


def setup_urllib(config):
    """ Setup urllib opener for auth and cookie handling """

    # Setup a (preemptive) basic auth handler
    password_mgr = urq.HTTPPasswordMgrWithPriorAuth()
    svr = config.Server
    password_mgr.add_password(None, f"http://{svr.host}:{svr.port}/",
        svr.user, svr.password, is_authenticated=True)
    auth_handler = urq.HTTPBasicAuthHandler(password_mgr)

    # Setup the cookie handler
    cookiejar = http.cookiejar.LWPCookieJar()
    cookie_handler = urq.HTTPCookieProcessor(cookiejar)

    # Create an opener using these handlers, and make it default
    opener = urq.build_opener(auth_handler, cookie_handler)
    urq.install_opener(opener)


def setup_basic_logging(cfgfile):
    """ Initial logging setup: log to file next to config file """

    # Determine log file name
    base, ext = splitext(cfgfile)
    if ext.lower() == '.toml':
        logfile = f'{base}.log'
    else:
        logfile = f'{cfgfile}.log'
    
    # Create handler with delayed creation of log file
    handlers = [logging.FileHandler(logfile, delay=True)]

    # Display what we log as-is, no level strings etc.
    logging.basicConfig(handlers=handlers, level=logging.INFO,
        format='%(message)s')


def setup_logging(config):
    """ Final logging setup: allow log location override in config """

    logdir:str = config.Local.logdir
    loglevel:str = config.Local.loglevel

    # Determine filename (without path)
    base, ext = splitext(basename(config.cfgfile))
    if ext.lower() == '.toml':
        logfile = f'{base}.log'
    else:
        logfile = f'{base}.{ext}.log'

    # Determine filename (with path)
    name = join(logdir, logfile)
    if not isabs(logdir):
        # Logdir not absolute: make it relative to dir config file is in
        name = join(dirname(config.cfgfile), name)

    # Make sure the log directory exists
    logdir = dirname(name)
    os.makedirs(logdir, exist_ok=True)

    # Replace the current logging handler with one using the newly
    # determined path
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.handlers.append(logging.FileHandler(name, 'a'))

    if loglevel is not None:
        logger.setLevel(loglevel.upper())

    # Log appends; create visible separation for this run
    logging.info(f"\n\n===== Starting at {str(datetime.datetime.now()).split('.')[0]}")
    

def unhandled_exception(exc_type, exc_value, exc_traceback):
    """ Handle otherwise unhandled exceptions by logging them """

    if exc_type == ConfigurationError:
        msg = exc_value.args[0]
        logging.error("\n%s", msg)
    else:
        msg = f"An error occurred; please see the log file for details.\n\n{exc_value}"
        logging.exception("\n##### Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))
    msgbox(msg, True)
    sys.exit(1)


def msgbox(msg, is_error=False):
    """ Display, if on Windows, a message box """

    if os.name == 'nt':
        if is_error:
            flags = 0x30
            title = "Error"
        else:
            flags = 0
            title = "Info"
        import ctypes
        MessageBox = ctypes.windll.user32.MessageBoxW
        MessageBox(None, msg, title, flags)
    else:
        print(msg)


def get_repo(config):
    if config.Source.type == 'github':
        from github import get_data
    elif config.Source.type == 'directory':
        from fsrepo import get_data
    else:
        raise ConfigurationError(f"Invalid repository type '{config.Source.type}' in configuration.")
    return get_data(config)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        msgbox(f"Usage: {sys.argv[0]} <cfgfile>", True)
        sys.exit(1)

    cfgfile = sys.argv[1]
    if not isabs(cfgfile) and not exists(cfgfile):
        cfgfile = join(dirname(__file__), cfgfile)
    
    if not exists(cfgfile) or not isfile(cfgfile):
        msgbox(f"File {cfgfile} not found.\nUsage: {sys.argv[0]} <cfgfile>", True)
        sys.exit(1)
    
    if not isabs(cfgfile):
        cfgfile = abspath(cfgfile)
    
    main(cfgfile)
    
    

