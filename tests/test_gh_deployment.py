from importlib import import_module
import binascii
from os.path import dirname, join, exists
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

# Check for server location and credentials for UDL-XML conversion
def get_credentials():
    name = join(dirname(__file__), 'server.toml')
    if not exists(name):
        return ''
    with open(name) as f:
        svr = f.read()
    return svr
SVR = get_credentials()


@pytest.mark.skipif(SVR=='', reason="No UDL-XML conversion server configured.")
@pytest.mark.usefixtures("reload_modules")
def test_build(tmpdir, get_build, validate_schema):
    """Retrieve and build specific packge."""
    
    cfg = CFG.format(deployment='false') + "\n" + SVR
    export = get_build(cfg, tmpdir)
    validate_schema(export, 'irisexport.xsd')
    # Check binary equality
    crc = binascii.crc32(export)
    assert crc == 663428536
    

@pytest.mark.skipif(SVR=='', reason="No UDL-XML conversion server configured.")
@pytest.mark.usefixtures("reload_modules")
def test_build_deployment(tmpdir, get_build, validate_schema):
    """Check creating deployment."""
    
    cfg = CFG.format(deployment='true') + "\n" + SVR
    export = get_build(cfg, tmpdir)
    tree = etree.parse(BytesIO(export))
    # Can't CRC file, export notes contain timestamp. Check contents.
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('/Class[@name="Strix.Background.ItemInfo"]') is not None, "Strix.Background.ItemInfo not in export"
    assert tree.find('/Routine[@name="Strix"]') is not None, "Strix.inc not in export"
    assert len(tree.findall('/Project')) == 1, "No project in export"
    assert len(tree.findall('/Project/Items/ProjectItem')) == 24, "Unexpected number of items in export"
    ptd_name = tree.find('/Project/Items/ProjectItem[24]').get('name')
    assert tree.find(f'/Document[@name="{ptd_name}"]') is not None, "Deployment document not in export"
    ptd = tree.find(f'/Document[@name="{ptd_name}"]/ProjectTextDocument')
    assert ptd is not None, "Embedded project text document not in deployment"
    subtree = etree.parse(StringIO(ptd.text))
    assert subtree.find('/Contents') is not None, "No Contents element in deployment"
    assert len(subtree.findall('/Contents/Item')) == 23, "Unexpected number of items in deployment"
    assert subtree.find('/Contents/Item[23]').text == 'Strix.INC', "Unexpected order of items in deployment"
    
    validate_schema(export, 'irisexport.xsd')
    

