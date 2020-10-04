
import os
from os.path import join, split, relpath, splitext, getmtime
from datetime import datetime, timezone
import logging

from config import get_config


def get_data(config):
    return FsRepo(config)


class FsRepo:
    def __init__(self, config):
        super().__init__() 
        self.config = config

        self.src_items = []
        self.data_items = []
        self.csp_items = []
        self.name:str = ''

        self.get_names()

    def get_names(self):
        dir = self.config.Directory.path
        self.name = split(dir)[-1]

        cfg = self.config.Source
        cspdir = cfg.cspdir
        srcdir = cfg.srcdir
        datadir = cfg.datadir

        encoding = self.config.Source.encoding

        for name in self.list_files(dir, False):
            skip = any(rx.match(name) for rx in self.config.skip_regexes)
            if skip:
                logging.debug('Skipping %s because config requested so', name)
                continue
            
            parts = name.split(os.sep)

            if parts[0] == cspdir:
                base = join(dir, cspdir)
                name = relpath(join(dir, name), base)
                if os.sep != '/':
                    name = '/'.join(name.split(os.sep))
                self.csp_items.append(FsRepoCspItem(base, name, encoding))

            elif parts[0] == datadir:
                base = join(dir, datadir)
                name = relpath(join(dir, name), base)
                if os.sep != '/':
                    name = '/'.join(name.split(os.sep))
                self.data_items.append(FsRepoItem(base, name, encoding))

            elif srcdir in ('', parts[0]):
                base = join(dir, srcdir)
                name = relpath(join(dir, name), base)
                if os.sep != '/':
                    name = '/'.join(name.split(os.sep))
                self.src_items.append(FsRepoItem(base, name, encoding))

            else:
                logging.debug(f"Skipping {name} as it's not in a configured directory.")


    def list_files(self, dir, is_flat):
        if is_flat:
            for entry in os.scandir(dir):
                if not entry.is_dir():
                    yield entry.name
            return
        
        for root, dirs, files in os.walk(dir):
            relative = relpath(root, dir)
            if relative == '.':
                relative = ''
            for file in files:
                yield join(relative, file)



class FsRepoItem:
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


class FsRepoCspItem(FsRepoItem):
    """CSP-type repository item."""

    @property
    def relpath(self):
        return '/' + self.item_name
    
    @property
    def is_text(self):
        name = self.item_name
        ext = splitext(name)[1]
        if not ext:
            return False
        ext = ext[1:]
        return ext.lower() in "csp,csr,xml,js,css,xsl,xsd,txt,html".split(',')

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


# ==========

def main():
    cfg = get_config()
    repo = get_data(cfg)

    for item in repo.src_items:
        print(item.name, len(item.data))

if __name__ == "__main__":
    main()
