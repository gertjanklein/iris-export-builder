from typing import Any
from importlib import import_module
from io import BytesIO

from lxml import etree

import pytest

import namespace as ns
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
def test_data_in_udl_tree(server_toml, tmp_path, src_tree_udl, get_build):
    """ Test that data (=XML) in an UDL source tree raises an error.

    Tests conversion in the main thread, so exceptions need no special
    handling.
    """

    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(path=src_tree_udl, srcdir='', datadir='')
    cfg = f"{cfg}\nthreads=1\n{server_toml}"

    # Getting export should fail at an attempt to convert the lookup
    # table from UDL to XML
    with pytest.raises(ValueError) as e:
        get_build(cfg, tmp_path)
    assert "Error converting" in e.value.args[0], "Wrong error message"


@pytest.mark.usefixtures("reload_modules")
def test_data_in_udl_tree_threads(server_toml, tmp_path, src_tree_udl, get_build):
    """ Test that data (=XML) in an UDL source tree raises an error.
    
    Specifically tests for conversion in threads; errors raised there
    should be re-raised in the main thread.
    """

    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(path=src_tree_udl, srcdir='', datadir='')
    cfg = f"{cfg}\nthreads=2\n{server_toml}"

    # Getting export should fail at an attempt to convert the lookup
    # table from UDL to XML
    with pytest.raises(ValueError) as e:
        get_build(cfg, tmp_path)
    assert "Error converting" in e.value.args[0], "Wrong error message"


@pytest.mark.usefixtures("reload_modules")
def test_data_separate(server_toml, tmp_path, src_tree_udl, get_build):
    """ Test that specifying data directory prevents UDL conversion.
    """

    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(path=src_tree_udl, srcdir='', datadir='data')
    cfg = f"{cfg}\nthreads=1\n{server_toml}"

    # Getting export should succeed, data directory not UDL to XML
    # converted
    export = get_build(cfg, tmp_path)

    # Check export is valid and contains class and data
    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('./Class[@name="tmp.a"]') is not None, "tmp.a not in export"
    assert tree.find('./Document[@name="Test.LUT"]') is not None, "Test.LUT not in export"


@pytest.mark.usefixtures("reload_modules")
def test_data_separate_threads(server_toml, tmp_path, src_tree_udl, get_build):
    """ Test that specifying data directory prevents UDL conversion.

    Specifically tests conversion in threads.
    """

    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(path=src_tree_udl, srcdir='', datadir='data')
    cfg = f"{cfg}\nthreads=2\n{server_toml}"

    # Getting export should succeed, data directory not UDL to XML
    # converted
    export = get_build(cfg, tmp_path)

    # Check export is valid and contains class and data
    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('./Class[@name="tmp.a"]') is not None, "tmp.a not in export"
    assert tree.find('./Document[@name="Test.LUT"]') is not None, "Test.LUT not in export"


@pytest.mark.usefixtures("reload_modules")
def test_error_no_server(tmp_path, get_build):
    """ Test UDL -> XML conversion server error.
    """

    # Server definition that should fail (invalid port)
    server_toml = "[Server]\nhost='localhost'\nport=55555\n"
    cfg = CFG.format(path=tmp_path, srcdir='', datadir='')
    cfg = f"{cfg}\n{server_toml}"

    # Connection failure should raise a configuration error
    with pytest.raises(ns.ConfigurationError) as e:
        get_build(cfg, tmp_path)
    assert "Error connecting" in e.value.args[0], "Wrong error message"


# =====

# Class export template (UDL)
CLS_TPL_UDL = """\
/// Non-latin: €ş.
Class {name}
{{
}}
"""

# Lookup table export template
LUT_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Document name="{name}.LUT">
<lookupTable>
<entry table="{name}" key="test_key">Non-latin: €ş.</entry>
</lookupTable>
</Document>
</Export>
"""


@pytest.fixture(scope="session")
def src_tree_udl(tmp_path_factory):
    """ Creates a source tree with source and data items.

    Returns the base directory for the source tree.
    """
    
    # Base source tree
    base = tmp_path_factory.mktemp("basic_source_tree_udl", numbered=False)

    # Add a (UDL) class
    dir = base / 'src'
    dir.mkdir(parents=True)
    file = dir / "a.cls"
    file.write_text(CLS_TPL_UDL.format(name="tmp.a"), encoding='UTF-8')

    # Add a lookup table
    dir = base / 'data'
    dir.mkdir(parents=True)
    file = dir / "Test.lut"
    file.write_text(LUT_TPL.format(name="Test"), encoding='UTF-8')

    return base

