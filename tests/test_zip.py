from importlib import import_module
from typing import Any

from lxml import etree

import pytest

from ziprepo import ZipRepo
builder = import_module("build-export") # type: Any


CFG = """
[Source]
type = "github"
srctype = "xml"
srcdir = 'src'
cspdir = 'csp'
datadir = 'data'
skip = [{skip}]
[CSP]
export = 'embed'
[Data]
export = 'embed'
[[CSP.parsers]]
regex = '((/csp)?/[^/]+)/(.+)'
app = '\\1'
item = '\\3'
nomatch = 'error'
[GitHub]
user = "u"
repo = "r"
tag = "t"
[Local]
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_all_types(src_tree_zipped, tmp_path, get_config):
    """ Tests loading from a zip repo file. """

    # Get parsed configuration
    toml = CFG + "\ntimestamps='update'"
    config = get_config(toml, tmp_path)

    # Create a ZipRepo from the zipped source tree, and initialize it
    repo = ZipRepo(config, src_tree_zipped)
    repo.get_names()

    # Create the export
    builder.run(config, repo)

    # Parse with ElementTree
    tree = etree.parse(str(tmp_path / 'out.xml'))

    # Make sure everything we expect is there
    assert tree.docinfo.root_name == 'Export'

    assert tree.find('/Class[@name="tmp.a"]') is not None, "tmp.a not in export"
    assert tree.find('/Class[@name="tmp.b"]') is not None, "tmp.b not in export"
    assert tree.find('/Class[@name="tmp.c.cc"]') is not None, "tmp.c.cc not in export"
    
    assert tree.find('/Routine[@name="Include"][@type="INC"]') is not None, "Routine.inc not in export"

    assert tree.find('/CSP[@name="hello.csp"]') is not None, "hello.csp not in export"
    assert tree.find('/CSP[@name="goodbye.csp"]') is not None, "goodbye.csp not in export"
    assert tree.find('/CSPBase64[@name="binary.bin"]') is not None, "binary.bin not in export"
    assert tree.find('/CSPBase64[@name="dat"]') is not None, "dat not in export or not binary"
    
    assert tree.find('/Document[@name="Test.LUT"]') is not None, "Test.LUT not in export"
    assert tree.find('/Document[@name="Test.LUT"]/lookupTable/entry[@table="Test"]') is not None, "Test entry of lookup table not in export"

    assert tree.find('/Document[@name="Ens.Config.DefaultSettings.esd"]') is not None, "Ens.Config.DefaultSettings.esd not in export"
    assert tree.find('/Document[@name="Ens.Config.DefaultSettings.esd"]/defaultSettings/item/[@item="Test"]') is not None, "Test default setting not in export"


