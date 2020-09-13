#!/usr/bin/env python3
# encoding: UTF-8

import os
from os.path import dirname, join, isabs, exists, splitext, basename
import re
import logging
import urllib.request as urq
import datetime
import http.cookiejar
import json
import base64

from lxml import etree

from config import get_config, ConfigurationError, msgbox
from deployment import append_export_notes


def main():
    # Get configuration and handle command line arguments
    config = get_config()
    
    # Setup basic auth handler for IRIS, if we need to convert UDL to XML
    if config.Source.srctype == 'udl':
        setup_urllib(config)

    # Get object representing repo
    repo = get_repo(config)

    # Create root element for export
    root = etree.Element('Export')
    root.attrib['generator'] = 'IRIS'
    root.attrib['version'] = '26'
    root.text = '\n'
    root.tail = '\n'

    # Create the export by adding nodes for each item
    skipped = create_export(config, repo, root)

    # Determine export filename and write the output
    export_name = get_export_name(config, repo.name)
    et = etree.ElementTree(root)
    et.write(export_name, xml_declaration=True, encoding="UTF-8")

    # Calculate total count of items handled
    itemcount = len(repo.src_items) + len(repo.data_items) + len(repo.csp_items) - skipped

    # If CSP items are to be exported to a separate file, do so
    if repo.csp_items and config.CSP.export == 'separate':
        csp_export_name, skipped = export_csp_separate(config, repo, export_name)
        itemcount -= skipped
        count1 = len(repo.src_items) + len(repo.data_items)
        count2 = len(repo.csp_items) - skipped
        logmsg = f"\nDone; added {count1} items to export in {export_name} and {count2} to {csp_export_name}.\n"
    else:
        logmsg = f"\nDone; added {itemcount} items to export in {export_name}.\n"
    
    # Give some feedback
    logging.info(logmsg)
    msgbox(f"Successfully exported {itemcount} items.")
    

def create_export(config, repo, root:etree.Element):
    """Create the export from the items in the repo object."""
    
    skipped = 0
    is_udl = config.Source.srctype == 'udl'
    parser = etree.XMLParser(strip_cdata=False)

    # Add IRIS source items.
    for item in repo.src_items:
        if is_udl:
            logging.info(f'Converting {item.name}')
            export = convert_to_xml(config, item)
        else:
            logging.info(f'Adding {item.name}')
            export = item.data
        export_root = etree.fromstring(export.encode('UTF-8'), parser=parser)
        if config.Source.type == 'directory':
            # Use local filesystem last update timestamp
            update_timestamp(export_root, item)
        else:
            # GitHub zip download timestamps are wrong; remove them
            remove_timestamps(export_root)
        for el in export_root:
            el.tail = '\n\n'
            root.append(el)

    # Add data items
    for item in repo.data_items:
        logging.info(f'Adding {item.name}')
        export_root = etree.fromstring(item.data.encode('UTF-8'), parser=parser)
        for el in export_root:
            el.tail = '\n\n'
            root.append(el)
    
    if config.Source.cspdir and config.CSP.export == 'embed':
        skipped = append_csp_items(config, repo, root)

    # Append export notes to make export usable as a deployment 
    if config.Local.deployment:
        append_export_notes(config, repo, root)
    
    return skipped


def export_csp_separate(config, repo, export_name):
    """ Creates a separate output file with CSP items. """

    # Determine export name
    base, ext = splitext(export_name)
    export_name = f"{base}_csp{ext}"

    # Create root export element
    root = etree.Element('Export')
    root.attrib['generator'] = 'IRIS'
    root.attrib['version'] = '25'
    root.text = '\n'
    root.tail = '\n'

    # Add the CSP items to it
    skipped = append_csp_items(config, repo, root)

    # Write to output file
    et = etree.ElementTree(root)
    et.write(export_name, xml_declaration=True, encoding="UTF-8")

    return export_name, skipped


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


def remove_timestamps(export:etree.Element):
    """Remove timestamp elements for classes in export."""

    tree = etree.ElementTree(export)
    for el in tree.xpath("/Export/Class/TimeChanged"):
        el.getparent().remove(el)
    for el in tree.xpath("/Export/Class/TimeCreated"):
        el.getparent().remove(el)


def update_timestamp(export:etree.Element, item):
    """Set timestamps for classes in export from item modified time."""

    ts = item.horolog
    for el in export:
        if el.tag != "Class": continue
        for subel in el:
            if subel.tag == "TimeChanged" or subel.tag == "TimeCreated":
                subel.text = ts


def append_csp_items(config, repo, root:etree.Element):
    """Append CSP items to the export."""
    
    skipped = 0
    for item in repo.csp_items:
        name = item.relpath
        split = split_csp(config, name)
        if not split:
            skipped += 1
            continue
        app, cspname = split
        logging.info(f'Adding {name} as app "{app}", item "{cspname}".')

        if item.is_text:
            name = 'CSP'
            data = etree.CDATA(item.data)
        else:
            name = 'CSPBase64'
            data = b'\n'+ base64.encodebytes(item.data)
        
        export = etree.Element(name)
        export.attrib['name'] = cspname
        export.attrib['application'] = app
        export.text = data
        export.tail = '\n\n'

        root.append(export)

    return skipped


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


def get_repo(config):
    if config.Source.type == 'github':
        from github import get_data
    elif config.Source.type == 'directory':
        from fsrepo import get_data
    else:
        raise ConfigurationError(f"Invalid repository type '{config.Source.type}' in configuration.")
    return get_data(config)


if __name__ == '__main__':
    main()
    
    

