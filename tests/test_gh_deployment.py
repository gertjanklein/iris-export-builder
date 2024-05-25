from importlib import import_module
import binascii
from io import BytesIO, StringIO
from typing import Any

from lxml import etree

import pytest

builder = import_module("build-export") # type: Any


# Configuration to retrieve a specific checkin of (part of) the Strix
# package from GitHub, and create an export from it; this should
# always yield the same result.
CFG = """
[Source]
type = "github"
srctype = "udl"
srcdir = 'src'
skip = [ "*Strix.SCM.*", "*Strix.Lib*", "*Strix.Test*", "*Strix.JSON*" ]
[GitHub]
user = "gertjanklein"
repo = "Strix"
tag = "840e7413371486b74920b2b4575e10cab390b44a"
[Local]
outfile = 'out.xml'
deployment = {deployment}
"""

@pytest.mark.usefixtures("reload_modules")
def test_build(tmpdir, server_toml, get_build, validate_schema):
    """Retrieve and build specific packge."""
    
    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(deployment='false') + "\nconverter='iris'\n" + server_toml
    export = get_build(cfg, tmpdir)
    validate_schema(export, 'irisexport.xsd')
    # Check binary equality
    crc = binascii.crc32(export)
    assert crc == 663428536
    

@pytest.mark.usefixtures("reload_modules")
def test_build_deployment(tmpdir, server_toml, get_build, validate_schema):
    """Check creating deployment."""
    
    if not server_toml:
        cfg = CFG.format(deployment='true') + "converter='builtin'\n"
    else:
        cfg = CFG.format(deployment='true') + "\n" + server_toml
    
    export = get_build(cfg, tmpdir)
    tree = etree.parse(BytesIO(export))
    # Can't CRC file, export notes contain timestamp. Check contents.
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('./Class[@name="Strix.Background.ItemInfo"]') is not None, \
        "Strix.Background.ItemInfo not in export"
    assert tree.find('./Routine[@name="Strix"]') is not None, "Strix.inc not in export"
    assert len(tree.findall('./Project')) == 1, "No project in export"
    assert len(tree.findall('./Project/Items/ProjectItem')) == 24, \
        "Unexpected number of items in export"
    ptd = tree.find('./Project/Items/ProjectItem[24]')
    assert ptd is not None, "Item[24] missing"
    ptd_name = ptd.get('name')
    assert tree.find(f'./Document[@name="{ptd_name}"]') is not None, \
        "Deployment document not in export"
    ptd = tree.find(f'./Document[@name="{ptd_name}"]/ProjectTextDocument')
    assert ptd is not None, "Embedded project text document not in deployment"
    subtree = etree.parse(StringIO(ptd.text))
    assert subtree.find('./Contents') is not None, "No Contents element in deployment"
    assert len(subtree.findall('./Contents/Item')) == 23, \
        "Unexpected number of items in deployment"
    tmp = subtree.find('./Contents/Item[23]')
    assert tmp is not None, "Item[23] missing"
    assert tmp.text == 'Strix.INC', "Unexpected order of items in deployment"
    
    validate_schema(export, 'irisexport.xsd')
    

