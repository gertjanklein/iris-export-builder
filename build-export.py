#!/usr/bin/env python3
# encoding: UTF-8

import sys, os
from os.path import dirname, join, isabs, abspath, exists, splitext, isfile
import logging
import urllib.request as urq
import datetime
import http.cookiejar
import json
import base64

from config import get_config, ConfigurationError
from deployment import append_export_notes


def main(inifile):
    # Set up logging to file next to ini file
    setup_logging(inifile)
    
    # Log unhandled exceptions
    sys.excepthook = unhandled_exception

    # Get configuration
    config = get_config(inifile)

    # Setup basic auth handler for IRIS, if we need to convert UDL to XML
    if config.Repo.srctype == 'udl':
        setup_urllib(config)

    # Log appends; create visible separation for this run
    logging.info(f"\n\n===== Starting at {str(datetime.datetime.now()).split('.')[0]}")
    
    # Get object representing repo
    repo = get_repo(config)

    # Determine export filename
    export_name = get_export_name(config, repo.name)

    # Create an export file containing all the items
    with open(export_name, 'w', encoding='UTF-8') as outfile:
        create_export(config, repo, outfile)
    
    # Give some feedback
    count = len(repo.src_items) + len(repo.csp_items)
    logging.info(f"\nDone; added {count} items to export in {export_name}.\n\n")
    msgbox(f"Exported {count} items to {export_name}.")

    

def create_export(config, repo, outfile):
    """Create the export from the items in the repo object."""
    is_open = False
    is_udl = config.Repo.srctype == 'udl'

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
    
    # If this is just CSP files, we must write the Export tag ourselves
    if not is_open:
        outfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        outfile.write('<Export generator="IRIS" version="26">\n')

    # If any CSP items, append them to the export
    if repo.csp_items:
        append_csp_items(repo, outfile)

    # Append export notes to make export usable as a deployment 
    if config.Local.deployment:
        append_export_notes(config, repo, outfile)

    # Close Export element
    outfile.write('</Export>\n')


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


def append_csp_items(repo, outfile):
    for item in repo.csp_items:
        name = item.filename
        logging.info(f'Adding {name}')

        # Split name in CSP app and item
        parts = name[1:].split('/')
        if parts[0] == 'csp' and len(parts) > 2:
            app = '/' + '/'.join(parts[0:2])
            cspname = '/'.join(parts[2:])
        else:
            app = '/' + parts[0]
            cspname = '/'.join(parts[1:])

        # Get CSP item data
        data = item.data
        
        if item.is_text:
            append_csp_text(app, cspname, data, outfile)
        else:
            append_csp_binary(app, cspname, data, outfile)


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
    replacements = { 'name': repo_name, 'timestamp': ts }

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


def setup_logging(inifile):
    """ Setup logging to file """

    # Determine log file name
    base, ext = splitext(inifile)
    if ext.lower() == '.toml':
        logfile = f'{base}.log'
    else:
        logfile = f'{inifile}.log'
    
    # Display what we log as-is, no level strings etc.
    logging.basicConfig(
        filename=abspath(logfile),
        level=logging.DEBUG,
        format='%(message)s')


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
    if config.Repo.type == 'github':
        from github import get_data
    elif config.Repo.type == 'directory':
        from fsrepo import get_data
    else:
        raise ConfigurationError(f"Invalid repository type '{config.Repo.type}' in configuration.")
    return get_data(config)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        msgbox(f"Usage: {sys.argv[0]} <inifile>", True)
        sys.exit(1)

    inifile = sys.argv[1]
    if not isabs(inifile) and not exists(inifile):
        inifile = join(dirname(__file__), inifile)
    
    if not exists(inifile) or not isfile(inifile):
        msgbox(f"File {inifile} not found.\nUsage: {sys.argv[0]} <inifile>", True)
        sys.exit(1)
    
    if not isabs(inifile):
        inifile = abspath(inifile)
    
    main(inifile)
    
    

