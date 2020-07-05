
"""Retrieve and parse a release from GitHub."""

import sys
from os.path import exists, isfile, splitext
import urllib.request as urq
import logging
import io
import zipfile

from config import get_config


def get_data(config):
    """Get the configured release from GitHub; return a ZipRepo for it."""

    gh = config['GitHub']
    url = f"https://github.com/{gh.user}/{gh.repo}/archive/{gh.tag}.zip"
    zf = get_zip(url, gh.token)
    return ZipRepo(config, zf)


class ZipRepo:
    """Handle a zipped repository."""

    def __init__(self, config, zip:zipfile.ZipFile):
        super().__init__() 
        self.config = config
        self.zip = zip

        self.src_items:ZipRepoItem = []
        self.csp_items:ZipRepoCspItem = []
        self.name:str = ''

        self.get_names()
    
    
    def get_names(self):
        """Get names from zipfile and split in basename, items, and CSP items."""
        
        zip_items = self.zip.infolist()

        cfg = self.config.Source
        cspdir = cfg.cspdir
        srcdir = cfg.srcdir

        # The first item in the zip file is the top-level directory
        base = zip_items[0].filename
        if base[-1] == '/': base = base[:-1]
        self.name = base

        # Process subsequent items
        for item in zip_items[1:]:
            name = item.filename

            # Ignore directory entries
            if name[-1] == '/': continue
            # First part is base dir, second (possibly) zip dir
            parts = name.split('/')
            # Skip .gitignore etc.
            if parts[-1][0] == '.': continue

            # Check for items we should skip (remove base directory name first)
            tmp = '/' + name.split('/', 1)[1]
            skip = any(rx.match(tmp) for rx in self.config.skip_regexes)
            if skip:
                logging.debug('Skipping %s because config requested so', tmp)
                continue

            if parts[1] == cspdir:
                self.csp_items.append(ZipRepoCspItem(self, item, cspdir))
            
            elif srcdir in ('', parts[1]):
                # Non-CSP items always have a type
                if not '.' in parts[-1]: continue
                self.src_items.append(ZipRepoItem(self, item, srcdir))


class ZipRepoItem:
    """Normal repostitory item."""
    def __init__(self, parent:ZipRepo, info:zipfile.ZipInfo, prefix):
        super().__init__()
        self.parent = parent
        self.info = info
        self.prefix = prefix

    @property
    def name(self):
        # Skip base directory name
        parts = self.info.filename.split('/')[1:]
        if parts[0] == self.prefix:
            parts = parts[1:]
        return '.'.join(parts)

    @property
    def filename(self):
         # Skip base directory name
        parts = self.info.filename.split('/')[1:]
        if parts[0] == self.prefix:
            parts = parts[1:]
        return '/' + '/'.join(parts)
       
    @property
    def data(self):
        encoding = self.parent.config.Source.encoding
        with self.parent.zip.open(self.info) as f:
            data = f.read()
        data = data.decode(encoding)

        # Unix IRIS servers choke on \r\n linefeeds in routines
        data = data.replace('\r', '')

        return data

class ZipRepoCspItem(ZipRepoItem):
    """CSP-type repository item."""

    @property
    def is_text(self):
        name = self.info.filename
        ext = splitext(name)[1]
        if not ext:
            return False
        ext = ext[1:]
        return ext.lower() in "csp,csr,xml,js,css,xsl,xsd,txt,html".split(',')

    @property
    def data(self):
        with self.parent.zip.open(self.info) as f:
            data = f.read()
        
        if self.is_text:
            encoding = self.parent.config.Source.encoding
            data = data.decode(encoding)
            data = data.replace('\r', '')

        return data


def get_zip(url, token):
    """Return a ZipFile object downloaded from a url."""

    logging.info(f'Retrieving {url}\n')
    headers = { 'Authorization': f'token {token}' } if token else {}
    rq = urq.Request(url, headers=headers)
    with urq.urlopen(rq) as rsp:
        data = io.BytesIO(rsp.read())
    return zipfile.ZipFile(data)



def main(cfgfile):
    cfg = get_config(cfgfile)
    zr = get_data(cfg)

    for item in zr.src_items:
        zi = item.info
        print(item.filename, zi.filename)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <configfile>")
        sys.exit(1)

    cfgfile = sys.argv[1]
    if not exists(cfgfile) or not isfile(cfgfile):
        print(f"File {cfgfile} not found.\nUsage: {sys.argv[0]} <configfile>")
        sys.exit(1)
    
    main(cfgfile)
