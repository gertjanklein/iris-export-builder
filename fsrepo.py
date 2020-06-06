
import sys, os
from os.path import join, split, relpath, exists, isfile

from config import get_config


def get_data(config):
    return FsRepo(config)


class FsRepo:
    def __init__(self, config):
        super().__init__() 
        self.config = config

        self.src_items = []
        self.csp_items = []
        self.name:str = ''

        self.get_names()

    def get_names(self):
        dir = self.config.Directory.path
        self.name = split(dir)[-1]

        if self.config.Repo.srcdir:
            dir = join(dir, self.config.Repo.srcdir)
        is_flat = self.config.Repo.structure == 'flat'
        
        for name in self.list_files(dir, is_flat):
            self.src_items.append(FsRepoItem(self, dir, name))


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
    def __init__(self, parent, base_dir, name):
        super().__init__()
        self.parent = parent
        self.base_dir = base_dir
        self.item_name = name

    @property
    def name(self):
        return self.item_name

    @property
    def filename(self):
        return join(self.base_dir, self.item_name)
       
    @property
    def data(self):
        encoding = self.parent.config.Repo.encoding
        with open(join(self.base_dir, self.item_name), 'r', encoding=encoding) as f:
            data = f.read()
        return data


# ==========

def main(cfgfile):
    cfg = get_config(cfgfile)
    repo = get_data(cfg)

    for item in repo.src_items:
        print(item.name, len(item.data))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <configfile>")
        sys.exit(1)

    cfgfile = sys.argv[1]
    if not exists(cfgfile) or not isfile(cfgfile):
        print(f"File {cfgfile} not found.\nUsage: {sys.argv[0]} <configfile>")
        sys.exit(1)
    
    main(cfgfile)
