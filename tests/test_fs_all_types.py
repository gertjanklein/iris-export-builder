from importlib import import_module
from typing import Any
from io import BytesIO

from lxml import etree

import pytest

builder = import_module("build-export") # type: Any


CFG = """
[Source]
type = "directory"
srctype = "xml"
srcdir = 'src'
cspdir = 'csp'
datadir = 'data'
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
"""


@pytest.mark.usefixtures("reload_modules")
def test_all_types(src_tree, get_build, validate_schema):
    """ Tests creating an export with src, csp, and data items. """

    cfg = CFG.format(path=src_tree)
    export = get_build(cfg, src_tree)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'

    assert tree.find('/Class[@name="tmp.a"]') is not None, "tmp.a not in export"
    assert tree.find('/Class[@name="tmp.b"]') is not None, "tmp.b not in export"
    assert tree.find('/Class[@name="tmp.c.cc"]') is not None, "tmp.c.cc not in export"
    
    assert tree.find('/Routine[@name="Include"][@type="INC"]') is not None, "Routine.inc not in export"

    assert tree.find('/CSP[@name="hello.csp"]') is not None, "hello.csp not in export"
    assert tree.find('/CSP[@name="goodbye.csp"]') is not None, "goodbye.csp not in export"
    assert tree.find('/CSPBase64[@name="binary.bin"]') is not None, "binary.bin not in export"
    
    assert tree.find('/Document[@name="Test.LUT"]') is not None, "Test.LUT not in export"
    assert tree.find('/Document[@name="Test.LUT"]/lookupTable/entry[@table="Test"]') is not None, "Test entry of lookup table not in export"

    assert tree.find('/Document[@name="Ens.Config.DefaultSettings.esd"]') is not None, "Ens.Config.DefaultSettings.esd not in export"
    assert tree.find('/Document[@name="Ens.Config.DefaultSettings.esd"]/defaultSettings/item/[@item="Test"]') is not None, "Test default setting not in export"

    validate_schema(export)


# -----

@pytest.mark.usefixtures("reload_modules")
def test_all_types_separate(src_tree, get_build_separate, validate_schema):
    """ Tests separate exports for source, CSP, and data """

    cfg = CFG.format(path=src_tree)
    cfg = cfg.replace("'embed'", "'separate'")
    src_export, csp_export, data_export = get_build_separate(cfg, src_tree)

    # === Check export of source items

    tree = etree.parse(BytesIO(src_export))
    assert tree.docinfo.root_name == 'Export'

    assert tree.find('/Class[@name="tmp.a"]') is not None, "tmp.a not in export"
    assert tree.find('/Class[@name="tmp.b"]') is not None, "tmp.b not in export"
    assert tree.find('/Class[@name="tmp.c.cc"]') is not None, "tmp.c.cc not in export"
    
    assert tree.find('/Routine[@name="Include"][@type="INC"]') is not None, "Routine.inc not in export"
    
    # There should be no CSP items and no data items in the export
    assert tree.find('/CSP[@name="hello.csp"]') is None, "hello.csp in export"
    assert tree.find('/Document[@name="Test.LUT"]') is None, "Test.LUT in export"

    validate_schema(src_export)

    # === Check export of CSP items

    tree = etree.parse(BytesIO(csp_export))
    assert tree.docinfo.root_name == 'Export'

    assert tree.find('/CSP[@name="hello.csp"]') is not None, "hello.csp not in export"
    assert tree.find('/CSP[@name="goodbye.csp"]') is not None, "goodbye.csp not in export"
    assert tree.find('/CSPBase64[@name="binary.bin"]') is not None, "binary.bin not in export"
    
    # There should be no source items and no data items in the export
    assert tree.find('/Class[@name="tmp.a"]') is None, "tmp.a in export"
    assert tree.find('/Document[@name="Test.LUT"]') is None, "Test.LUT in export"

    validate_schema(csp_export)

    # === Check export of data items

    tree = etree.parse(BytesIO(data_export))
    assert tree.docinfo.root_name == 'Export'

    assert tree.find('/Document[@name="Test.LUT"]') is not None, "Test.LUT not in export"
    assert tree.find('/Document[@name="Test.LUT"]/lookupTable/entry[@table="Test"]') is not None, "Test entry of lookup table not in export"

    assert tree.find('/Document[@name="Ens.Config.DefaultSettings.esd"]') is not None, "Ens.Config.DefaultSettings.esd not in export"
    assert tree.find('/Document[@name="Ens.Config.DefaultSettings.esd"]/defaultSettings/item/[@item="Test"]') is not None, "Test default setting not in export"

    # There should be no source items and no CSP items in the export
    assert tree.find('/Class[@name="tmp.a"]') is None, "tmp.a in export"
    assert tree.find('/CSP[@name="hello.csp"]') is None, "hello.csp in export"

    validate_schema(data_export)


