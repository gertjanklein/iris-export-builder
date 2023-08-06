
from unittest.mock import patch

import pytest

import fsrepo
import ziprepo


CFG = """
[Source]
type = '{type}'
srctype = "xml"
srcdir = 'src'
cspdir = 'csp'
datadir = 'data'
[CSP]
export = 'none'
[Data]
export = 'embed'
[Directory]
path = '{path}'
[GitHub]
user = "u"
repo = "r"
tag = "t"
[Local]
outfile = 'out.xml'
deployment = false
sort = true
"""


@pytest.mark.usefixtures("reload_modules")
def test_sort_fs(src_tree, get_config):
    """Test sorting of filesystem repository"""
    
    cfg = CFG.format(path=src_tree, type='directory')
    cfg_ns = get_config(cfg, src_tree)
    
    # Get the files in original (undetermined) order
    files = list(fsrepo.FsRepo.list_files(src_tree))
    
    # Sort, and move last item to first position
    files.sort(key=lambda s: s.lower())
    files.insert(0, files.pop())
    
    # Confirm the last item is now the first
    assert files[0] == 'src\\Include.inc.xml'
    
    # Get the repo using this no longer sorted input
    with patch('fsrepo.FsRepo.list_files') as mock_list_files:
        mock_list_files.return_value = files
        repo:fsrepo.FsRepo = fsrepo.get_data(cfg_ns)
    
    # We expect 4 source items
    assert len(repo.src_items) == 4, f"Unexpected number of source items: {len(repo.src_items)}"
    assert repo.src_items[0].name == 'a.cls.xml', "Expected a.cls.xml to be sorted first"


@pytest.mark.usefixtures("reload_modules")
def test_sort_zip(src_tree_zipped, get_config, tmp_path):
    """Test sorting of zipped repository"""
    
    cfg = CFG.format(path=tmp_path, type='github')
    cfg_ns = get_config(cfg, tmp_path)
    
    # Get the list of items in the zip file
    items = src_tree_zipped.infolist()
    
    # Sort, and move last item to first position
    items.sort(key=lambda s: s.filename.lower())
    items.insert(1, items.pop())
    
    # Confirm the last item is now the first
    assert items[1].filename == 'basic_source_tree/src/Include.inc.xml'
    
    with patch.object(src_tree_zipped, 'infolist', return_value=items):
        repo = ziprepo.ZipRepo(cfg_ns, src_tree_zipped)
        repo.get_names()
    
    assert len(repo.src_items) == 4, f"Unexpected number of source items: {len(repo.src_items)}"
    assert repo.src_items[0].name == 'a.cls.xml', f"Expected 'a.cls.xml' to be sorted first, not '{repo.src_items[0].name}'"

