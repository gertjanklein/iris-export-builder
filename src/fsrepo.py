"""Retrieve and parse a release from the filesystem."""

from __future__ import annotations
from typing import List, Sequence

import os
from os.path import join, split, relpath, getmtime
from datetime import datetime, timezone
import logging

from repo import Repository, RepositorySourceItem, RepositoryCspItem, RepositoryDataItem


def get_data(config):
    """ Returns an FsRepo instance based on config """
    
    repo = FsRepo(config)
    repo.get_names()
    return repo


class FsRepo(Repository):
    """ Represents a filesystem repository """
    
    src_items:List[FsRepoItem]
    csp_items:List[FsRepoCspItem]
    data_items:List[FsRepoDataItem]

    def get_names(self):
        """ Scans the filesystem and adds appropriate items """
        
        dir = self.config.Directory.path
        self.name = split(dir)[-1]

        cfg = self.config.Source
        cspdir = cfg.cspdir
        srcdir = cfg.srcdir
        datadir = cfg.datadir

        encoding = self.config.Source.encoding

        for name in self.list_files(dir):
            # Normalize to forward slashes for use in regexes below
            norm = '/' + (name.replace(os.sep, '/') if os.sep != '/' else name)
            skip = any(rx.match(norm) for rx in self.config.skip_regexes)
            if skip:
                logging.debug('Skipping %s because item in "skip" list', name)
                continue
            
            if self.config.take_regexes:
                if not any(rx.match(norm) for rx in self.config.take_regexes):
                    logging.debug('Skipping %s because not in "take" list', name)
                    continue
            
            parts = name.split(os.sep)

            if path_matches(cspdir, parts):
                base = join(dir, cspdir)
                name = relpath(join(dir, name), base)
                if os.sep != '/':
                    name = '/'.join(name.split(os.sep))
                self.csp_items.append(FsRepoCspItem(base, name, encoding))

            elif path_matches(datadir, parts):
                base = join(dir, datadir)
                name = relpath(join(dir, name), base)
                if os.sep != '/':
                    name = '/'.join(name.split(os.sep))
                self.data_items.append(FsRepoDataItem(base, name, encoding))

            elif srcdir == '' or path_matches(srcdir, parts):
                base = join(dir, srcdir)
                name = relpath(join(dir, name), base)
                if os.sep != '/':
                    name = '/'.join(name.split(os.sep))
                self.src_items.append(FsRepoItem(base, name, encoding))

            else:
                logging.debug("Skipping %s as it's not in a configured directory.", name)
    
        if self.config.Local.sort:
            self.src_items.sort()
            self.csp_items.sort()
            self.data_items.sort()
            
    
    @staticmethod
    def list_files(dir):
        """ Lists files in directory recursively """
        
        for root, dirnames, files in os.walk(dir):
            dirnames[:] = [ n for n in dirnames if not n.startswith('.') ]
            relative = relpath(root, dir)
            if relative == '.':
                relative = ''
            for file in files:
                yield join(relative, file)


class FsRepoItem(RepositorySourceItem):
    """ Represents a single item in a filesystem repository """
    
    def __init__(self, base_dir, name, encoding):
        super().__init__()
        self.base_dir = base_dir
        self.item_name = name
        self.encoding = encoding

    @property
    def name(self):
        return self.item_name

    @property
    def filename(self):
        return join(self.base_dir, self.item_name)
        
    @property
    def horolog(self):
        # Get file timestamp: UTC since 1970-01-01
        ts = getmtime(self.filename)
        # Make TZ aware
        dt = datetime.fromtimestamp(ts).replace(tzinfo=timezone.utc)
        # Get timestamp in local time, and convert to horolog offset
        ts  = dt.timestamp() / 86400 + 47117
        # Split date and time
        d, t = divmod(ts, 1)
        # Date as integer, time as seconds since midnight
        d, t = int(d), round(t*86400, 3)
        # Return horolog format
        return f"{d},{t}"

    @property
    def data(self):
        encoding = self.encoding
        with open(join(self.base_dir, self.item_name), 'r', encoding=encoding) as f:
            data = f.read()
        return data


class FsRepoCspItem(RepositoryCspItem, FsRepoItem):
    """CSP-type repository item."""

    @property
    def relpath(self):
        return '/' + self.item_name
    
    @property
    def data(self):
        if self.is_text:
            mode, encoding = 'rt', self.encoding
        else:
            mode, encoding = 'rb', None
        with open(join(self.base_dir, self.item_name), mode, encoding=encoding) as f:
            data = f.read()
        
        if self.is_text:
            data = data.replace('\r', '')

        return data


class FsRepoDataItem(RepositoryDataItem, FsRepoItem):
    pass


def path_matches(cfgdir:str, parts:Sequence[str]):
    # Normalize to forward slashes
    cfgdir = cfgdir.replace('\\', '/')
    cfg = cfgdir.split('/')
    return parts[0:len(cfg)] == cfg
