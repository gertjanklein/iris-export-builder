
"""Retrieve and parse a release from GitHub."""

from os.path import splitext
import urllib.request as urq
import logging
import io
from zipfile import ZipFile, ZipInfo


def get_data(config):
    """Get the configured release from GitHub; return a ZipRepo for it."""

    gh = config['GitHub']
    url = f"https://github.com/{gh.user}/{gh.repo}/archive/{gh.tag}.zip"
    zf = get_zip(url, gh.token)
    return ZipRepo(config, zf)


class ZipRepo:
    """Handle a zipped repository."""

    def __init__(self, config, zip:ZipFile):
        super().__init__() 
        self.config = config
        self.zip = zip

        self.src_items:ZipRepoItem = []
        self.data_items:ZipRepoItem = []
        self.csp_items:ZipRepoCspItem = []
        self.name:str = ''

        self.get_names()
    
    
    def get_names(self):
        """Get names from zipfile and split in basename, items, and CSP items."""
        
        zip_items = self.zip.infolist()

        cfg = self.config.Source
        cspdir = cfg.cspdir
        srcdir = cfg.srcdir
        datadir = cfg.datadir

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

            # Configure separately for CSP and source?
            encoding = self.config.Source.encoding

            if parts[1] == cspdir:
                self.csp_items.append(ZipRepoCspItem(self.zip, item, cspdir, encoding))
            
            # Data is XML export, already encoded in UTF-8
            elif parts[1] == datadir:
                self.data_items.append(ZipRepoItem(self.zip, item, cspdir, 'UTF-8'))
            
            elif srcdir in ('', parts[1]):
                # Non-CSP items always have a type
                if not '.' in parts[-1]: continue
                self.src_items.append(ZipRepoItem(self.zip, item, srcdir, encoding))


class ZipRepoItem:
    """Normal repostitory item."""
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
        return '.'.join(parts)

    @property
    def data(self):
        encoding = self.encoding
        with self.zip.open(self.info) as f:
            data = f.read()
        data = data.decode(encoding)

        # Unix IRIS servers choke on \r\n linefeeds in routines
        data = data.replace('\r', '')

        return data

class ZipRepoCspItem(ZipRepoItem):
    """CSP-type repository item."""

    @property
    def relpath(self):
         # Skip base directory name
        parts = self.info.filename.split('/')[1:]
        if parts[0] == self.prefix:
            parts = parts[1:]
        return '/' + '/'.join(parts)
       
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
        with self.zip.open(self.info) as f:
            data = f.read()
        
        if self.is_text:
            encoding = self.encoding
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
    return ZipFile(data)

