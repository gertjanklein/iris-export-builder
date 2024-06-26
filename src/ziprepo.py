""" Defines a source tree inside a zipfile
"""

from __future__ import annotations
from typing import List, Sequence

import logging
from zipfile import ZipFile, ZipInfo

from repo import Repository, RepositorySourceItem, RepositoryCspItem, RepositoryDataItem


class ZipRepo(Repository):
    """Handle a zipped repository."""
    
    src_items:List[ZipRepoItem]
    csp_items:List[ZipRepoCspItem]
    data_items:List[ZipRepoDataItem]

    def __init__(self, config, zip:ZipFile):
        super().__init__(config) 
        self.zip = zip
    

    def get_names(self):
        """Get names from zipfile and split in basename, items, and CSP items."""
        
        zip_items = self.zip.infolist()

        cfg = self.config.Source
        cspdir = cfg.cspdir
        srcdir = cfg.srcdir
        datadir = cfg.datadir

        # The first item in the zip file is the top-level directory
        base = zip_items[0].filename
        if base[-1] == '/':
            base = base[:-1]
        self.name = base
        
        # Process subsequent items
        for item in zip_items[1:]:
            name = item.filename

            # Ignore directory entries
            if name[-1] == '/':
                continue
            # First part is base dir, second (possibly) zip dir
            parts = name.split('/')
            # Skip .gitignore etc.
            if parts[-1][0] == '.':
                continue

            # Check for items we should skip/take (remove base directory name first)
            tmp = '/' + name.split('/', 1)[1]
            skip = any(rx.match(tmp) for rx in self.config.skip_regexes)
            if skip:
                logging.debug('Skipping %s because item in "skip" list', name)
                continue
            
            if self.config.take_regexes:
                if not any(rx.match(tmp) for rx in self.config.take_regexes):
                    logging.debug('Skipping %s because not in "take" list', name)
                    continue
            
            # Configure separately for CSP and source?
            encoding = self.config.Source.encoding

            if path_matches(cspdir, parts[1:]):
                self.csp_items.append(ZipRepoCspItem(self.zip, item, cspdir, encoding))
            
            # Data is XML export, already encoded in UTF-8
            elif path_matches(datadir, parts[1:]):
                self.data_items.append(ZipRepoDataItem(self.zip, item, datadir, 'UTF-8'))
            
            elif srcdir == '' or path_matches(srcdir, parts[1:]):
                # Non-CSP items always have a type
                if not '.' in parts[-1]:
                    continue
                self.src_items.append(ZipRepoItem(self.zip, item, srcdir, encoding))
        
        if self.config.Local.sort:
            self.src_items.sort()
            self.csp_items.sort()
            self.data_items.sort()
            


class ZipRepoItem(RepositorySourceItem):
    """ Source repostitory item. """
    def __init__(self, zip:ZipFile, info:ZipInfo, prefix, encoding):
        super().__init__()
        self.zip = zip
        self.info = info
        self.prefix = prefix
        self.encoding = encoding

    @property
    def name(self):
        # Skip base directory name
        parts = self.info.filename.split('/')[1:]
        if parts[0] == self.prefix:
            parts = parts[1:]
        return '/'.join(parts)

    @property
    def data(self):
        encoding = self.encoding
        with self.zip.open(self.info) as f:
            data = f.read()
        data = data.decode(encoding)

        # Unix IRIS servers choke on \r\n linefeeds in routines
        data = data.replace('\r', '')

        return data


class ZipRepoCspItem(RepositoryCspItem, ZipRepoItem):
    """ CSP-type repository item. """

    @property
    def relpath(self):
         # Skip base directory name
        parts = self.info.filename.split('/')[1:]
        if parts[0] == self.prefix:
            parts = parts[1:]
        return '/' + '/'.join(parts)
       
    @property
    def data(self):
        with self.zip.open(self.info) as f:
            data = f.read()
        
        if self.is_text:
            encoding = self.encoding
            data = data.decode(encoding)
            data = data.replace('\r', '')

        return data


class ZipRepoDataItem(RepositoryDataItem, ZipRepoItem):
    """ Data repository item. """


def path_matches(cfgdir:str, parts:Sequence[str]):
    # Normalize to forward slashes
    cfgdir = cfgdir.replace('\\', '/')
    cfg = cfgdir.split('/')
    return parts[0:len(cfg)] == cfg


