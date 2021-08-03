from __future__ import annotations
from typing import Sequence, Optional

import os
from os.path import dirname, join, isabs, exists, splitext, basename
from io import BytesIO

import re
import datetime
import logging

from lxml import etree

import namespace as ns
from config import ConfigurationError
from repo import RepositoryItem, RepositoryCspItem


class ExportFile:
    """Represents a file with items to export"""

    # The configuration object
    config:ns.Namespace

    # The filename to export to
    filename:str

    # The items (in their 'repo' representation)
    items:Sequence[RepositoryItem]

    # The root element of the export to create
    root:Optional[etree.Element]

    
    def __init__(self, config, filename, items=None):
        self.config = config
        self.filename = filename
        self.items = items or []
        self.root = None


    def write(self):
        """Creates the export and writes it to the output file"""

        # Get export as binary data
        data = self.get_export_data()

        # Write to output file
        with open(self.filename, mode='wb') as f:
            f.write(data)
        

    def get_export_data(self) -> bytes:
        """Create and return export as bytes"""

        # Create export as lxml tree, if not already done
        if self.root is None:
            self.create_export()

        # Convert to bytes
        et = etree.ElementTree(self.root)
        export = BytesIO()
        et.write(export, xml_declaration=True, encoding="UTF-8")

        # Get binary data, and normalize line endings
        data = export.getvalue()
        data = data.replace(b'\r', b'')
        data = data.replace(b'\n', b'\r\n')

        return data


    def create_export(self) -> etree.Element:
        """Create the export from the items in this object."""
        
        # Create root element for export
        self.root = root = etree.Element('Export')
        root.text = '\n'
        root.tail = '\n'

        minver = maxver = 0
        parser = etree.XMLParser(strip_cdata=False)

        # How to handle timestamps ('clear', 'update', 'leave')
        timestamps = self.config.Local.timestamps
        # If we get data from GitHub, we get nonsense timestamps and
        # have no better info, so clear them regardless of setting
        if self.config.Source.srctype == 'udl' and self.config.Source.type == 'github':
            timestamps = 'clear'

        for item in self.items:
            # Get the lxml element for this item
            item_root = item.get_xml_element()

            if item.kind == 'csp':
                # CSP item is not wrapped in an Export element, add directly
                assert isinstance(item, RepositoryCspItem)
                logging.info(f'Adding {item.name} as app "{item.csp_application}", item "{item.csp_name}"')
                root.append(item_root)
                continue
            
            logging.info(f'Adding {item.name}')
            if 'version' in item_root.attrib:
                version = int(item_root.attrib['version'])

                # Save minimum and maximum version values
                if not minver or minver > version: minver = version
                if version > maxver: maxver = version

            # Handle item timestamps
            if timestamps == 'clear':
                self.remove_timestamps(item_root)
            elif timestamps == 'update':
                if ts := item.horolog:
                    self.update_timestamp(item_root, ts)
                else:
                    self.remove_timestamps(item_root)
            
            for el in item_root:
                el.tail = '\n\n'
                root.append(el)
        
        # Set version and generator attributes
        ver = maxver or minver or 25
        root.attrib['generator'] = 'IRIS' if ver > 25 else 'Cache'
        root.attrib['version'] = str(ver)


    def remove_timestamps(self, item_root:etree.Element):
        """Remove timestamp elements for classes in export."""

        tree = etree.ElementTree(item_root)
        for el in tree.xpath("/Export/Class/TimeChanged"):
            el.getparent().remove(el)
        for el in tree.xpath("/Export/Class/TimeCreated"):
            el.getparent().remove(el)


    def update_timestamp(self, item_root:etree.Element, horolog):
        """Set timestamps for classes in export to modified time."""

        for el in item_root:
            if el.tag != "Class":
                continue
            for tag in ("TimeChanged", "TimeCreated"):
                subel = el.find(tag)
                if subel is None:
                    # Add the element at the first position of the parent
                    subel = etree.Element(tag)
                    subel.tail = '\n'
                    el.insert(0, subel)
                subel.text = horolog


def get_files(config, repo):
    """ Splits the items into one or more ExportFile objects
    """

    export_files = []
    main_name = get_export_name(config, repo.name)
    main_export = ExportFile(config, main_name)
    export_files.append(main_export)

    # Export of code items
    for item in repo.src_items:
        item.is_udl = config.Source.srctype == 'udl'
        main_export.items.append(item)

    # Export of data items
    if repo.data_items and not config.Data.export == 'none':
        if config.Data.export == 'embed':
            main_export.items.extend(repo.data_items)
        else:
            name, ext = splitext(main_name)
            name = f'{name}_data{ext}'
            data_export = ExportFile(config, name, repo.data_items)
            export_files.append(data_export)
    
    # Export of CSP items
    if repo.csp_items and not config.CSP.export == 'none':
        if config.CSP.export == 'embed':
            csp_export = main_export
        else:
            name, ext = splitext(main_name)
            name = f'{name}_csp{ext}'
            csp_export = ExportFile(config, name)
            export_files.append(csp_export)

        for item in repo.csp_items:
            name = item.relpath
            split = split_csp(config, name)
            if split is None:
                continue
            parser, item.csp_application, item.csp_name = split
            csp_export.items.append(item)

    return export_files


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
        
        return parser, app, page
    
    return None


