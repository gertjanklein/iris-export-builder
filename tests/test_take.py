from importlib import import_module
from io import BytesIO

from lxml import etree

import pytest

builder = import_module("build-export")


CFG = """
[Source]
type = "directory"
srctype = "xml"
srcdir = 'src'
cspdir = 'csp'
datadir = 'data'
skip = [{skip}]
take = [{take}]
[CSP]
export = 'embed'
[Data]
export = 'embed'
[[CSP.parsers]]
regex = '((/csp)?/[^/]+)/(.+)'
app = '\\1'
item = '\\3'
nomatch = 'error'
[Directory]
path = '{path}'
[Local]
outfile = 'out.xml'
loglevel = 'debug'
"""


@pytest.mark.usefixtures("reload_modules")
def test_take_basic(src_tree, tmp_path, get_build, validate_schema):
    """Basic test for take"""

    # Get parsed configuration
    paths = '/csp/app/hello.csp', '/data/Test*', '/src/a.cls.xml'
    takes = ','.join((f"'{p}'" for p in paths))
    
    cfg = CFG.format(path=src_tree, skip='', take=takes)
    xml = get_build(cfg, tmp_path)

    # Parse with ElementTree
    tree = etree.parse(BytesIO(xml))
    assert tree.docinfo.root_name == 'Export'
    
    export = tree.getroot()
    assert len(export) ==  3, "Expect 3 items in export"
    
    # Make sure the things we skipped are not in the export
    assert tree.find('./CSP[@name="hello.csp"]') is not None, "hello.csp in export"
    assert tree.find('./Document[@name="Test.LUT"]') is not None, "Test.LUT in export"
    assert tree.find('./Class[@name="tmp.a"]') is not None, "tmp.a in export"

    validate_schema(xml)


@pytest.mark.usefixtures("reload_modules")
def test_skip_overrides_take(src_tree, tmp_path, get_build, validate_schema):
    """Tests that skip has priority over take"""

    # Get parsed configuration
    paths = '/csp/app/hello.csp', '/data/Test*', '/src/a.cls.xml'
    takes = ','.join((f"'{p}'" for p in paths))
    skips = "'/csp/app/hello.csp'"
    
    cfg = CFG.format(path=src_tree, skip=skips, take=takes)
    xml = get_build(cfg, tmp_path)

    # Parse with ElementTree
    tree = etree.parse(BytesIO(xml))
    assert tree.docinfo.root_name == 'Export'
    
    export = tree.getroot()
    assert len(export) ==  2, "Expect 2 items in export"
    
    # Make sure the things we skipped are not in the export
    assert tree.find('./CSP[@name="hello.csp"]') is None, "hello.csp must not in export"
    assert tree.find('./Document[@name="Test.LUT"]') is not None, "Test.LUT in export"
    assert tree.find('./Class[@name="tmp.a"]') is not None, "tmp.a in export"

    validate_schema(xml)




