from typing import Any
from importlib import import_module
from io import BytesIO

from lxml import etree

import pytest

builder = import_module("build-export") # type: Any


CFG = """
[Source]
type = "directory"
srctype = "udl"
srcdir = '{srcdir}'
datadir = '{datadir}'
[Directory]
path = '{path}'
[Local]
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_export_version_25(server_toml, tmp_path, src_tree_udl, get_build):
    """ Test conversion with export version override 25
    """

    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(path=src_tree_udl, srcdir='', datadir='')
    cfg = f"{cfg}\nexport_version=25\n{server_toml}"

    export = get_build(cfg, tmp_path)
    
    # Check export is valid and contains class
    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('/Class[@name="tmp.a"]') is not None, "tmp.a not in export"
    
    root = tree.getroot()
    assert root.attrib['version'] == '25', "Version not 25"
    assert root.attrib['generator'] == 'Cache', "Generator not Cache"


@pytest.mark.usefixtures("reload_modules")
def test_export_version_26(server_toml, tmp_path, src_tree_udl, get_build):
    """ Test conversion with export version override 26
    """

    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(path=src_tree_udl, srcdir='', datadir='')
    cfg = f"{cfg}\nexport_version=26\n{server_toml}"

    export = get_build(cfg, tmp_path)
    
    # Check export is valid and contains class
    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('/Class[@name="tmp.a"]') is not None, "tmp.a not in export"
    
    root = tree.getroot()
    assert root.attrib['version'] == '26', "Version not 26"
    assert root.attrib['generator'] == 'IRIS', "Generator not IRIS"



# =====


@pytest.fixture(scope="session")
def src_tree_udl(tmp_path_factory):
    """ Creates a source tree with source and data items.

    Returns the base directory for the source tree.
    """
    
    # Base source tree
    base = tmp_path_factory.mktemp("source", numbered=False)

    # Add a (UDL) class
    dir = base / 'src'
    dir.mkdir(parents=True)
    file = dir / "a.cls"
    file.write_text(CLS_TPL_UDL.format(name="tmp.a"), encoding='UTF-8')

    return base


# Class export template (UDL)
CLS_TPL_UDL = """\
/// Non-latin: €ş.
Class {name}
{{
}}
"""
