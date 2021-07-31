from importlib import import_module
from typing import Any
from io import BytesIO
from pathlib import Path

from lxml import etree

import pytest

builder = import_module("build-export") # type: Any


# Tests creating a combined export, containing items of all three
# types (source, CSP and data). Uses non-Latin1 content to make
# sure encoding/decoding works properly.


CFG = """
[Source]
type = "directory"
srctype = "xml"
srcdir = 'src'
cspdir = 'csp'
datadir = 'data'
[CSP]
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


@pytest.mark.usefixtures("reload_modules", "create_src_tree")
def test_all_types(tmp_path, get_build, validate_schema):
    """ Tests creating an export with src, csp, and data items. """

    cfg = CFG.format(path=tmp_path)
    export = get_build(cfg, tmp_path)

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


# =====

# Class export template (XML)
CLS_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Class name="{name}">
<Description>Non-latin: €ş.</Description>
<Super>%RegisteredObject</Super>
</Class>
</Export>
"""

INC_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Routine name="Include" type="INC"><![CDATA[
#define Hello "World €ş."
]]></Routine>
</Export>
"""

# CSP file template
CSP_TPL = """\
<!DOCTYPE html>
<html>
<head><title>{name}</title></head>
<body>
<h1>{name}</h1>
Non-latin: €ş.
</body>
</html>
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

# Ensemble system default settings export template
ESD_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Document name="Ens.Config.DefaultSettings.esd">
<defaultSettings>
<item production="*" item="Test" class="*" setting="Test" value="Non-latin: €ş."><Deployable>true</Deployable></item>
</defaultSettings>
</Document>
</Export>
"""


@pytest.fixture(scope="function")
def create_src_tree(tmp_path:Path):
    # Two classes directly in the root of the source dir
    dir = tmp_path / 'src'
    dir.mkdir(parents=True)
    for name in 'a', 'b':
        file = dir / f"{name}.xml"
        file.write_text(CLS_TPL.format(name=f"tmp.{name}"), encoding='UTF-8')
    
    # A class one level deeper
    dir = tmp_path / 'src' / 'c'
    dir.mkdir(parents=True)
    file = dir / "cc.xml"
    file.write_text(CLS_TPL.format(name="tmp.c.cc"), encoding='UTF-8')
    
    # An include file
    dir = tmp_path / 'src'
    file = dir / "Include.inc"
    file.write_text(INC_TPL, encoding='UTF-8')
    
    # Two csp files under application directory /app
    dir = tmp_path / 'csp' / 'app'
    dir.mkdir(parents=True)
    for name in 'hello', 'goodbye':
        file = dir / f"{name}.csp"
        file.write_text(CSP_TPL.format(name=name), encoding='UTF-8')
    
    # A binary-type CSP file (does not need actual 'binary' data)
    file = dir / "binary.bin"
    file.write_text('abc')

    # Data dir
    dir = tmp_path / 'data'
    dir.mkdir(parents=True)

    # ... with a lookup table
    file = dir / "Test.lut"
    file.write_text(LUT_TPL.format(name="Test"), encoding='UTF-8')

    # ... and a systems default settings export
    file = dir / "Settings.esd"
    file.write_text(ESD_TPL, encoding='UTF-8')
    
    