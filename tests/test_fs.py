from importlib import import_module
from typing import Any
from io import BytesIO
from pathlib import Path

from lxml import etree

import pytest

builder = import_module("build-export") # type: Any


# XML class template
CLASS_XML_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Class name="{name}">
<Super>%RegisteredObject</Super>
</Class>
</Export>
"""

CFG = """
[Source]
type = "directory"
srctype = "xml"
srcdir = '{srcdir}'
[Directory]
path = '{path}'
[Local]
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules", "create_src_tree")
def test_subpath_all(tmp_path, get_build):
    cfg = CFG.format(path=tmp_path, srcdir='src')
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('./Class[@name="tmp.cls1"]') is not None, "tmp.cls1 not in export"
    assert tree.find('./Class[@name="tmp.cls2"]') is not None, "tmp.cls2 not in export"


@pytest.mark.usefixtures("reload_modules", "create_src_tree")
def test_subpath_a(tmp_path, get_build):
    cfg = CFG.format(path=tmp_path, srcdir='src/a')
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('./Class[@name="tmp.cls1"]') is not None, "tmp.cls1 not in export"
    assert tree.find('./Class[@name="tmp.cls2"]') is None, "tmp.cls2 in export"


@pytest.mark.usefixtures("reload_modules", "create_src_tree")
def test_subpath_b(tmp_path, get_build):
    cfg = CFG.format(path=tmp_path, srcdir='src/b')
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('./Class[@name="tmp.cls1"]') is None, "tmp.cls1 in export"
    assert tree.find('./Class[@name="tmp.cls2"]') is not None, "tmp.cls2 not in export"


# =====

@pytest.fixture(scope="function")
def create_src_tree(tmp_path:Path):
    dir1 = tmp_path / "src" / "a"
    dir1.mkdir(parents=True)
    cls1 = dir1 / "cls1.xml"
    cls1.write_text(CLASS_XML_TPL.format(name="tmp.cls1"))

    dir2 = tmp_path / "src" / "b"
    dir2.mkdir(parents=True)
    cls2 = dir2 / "cls2.xml"
    cls2.write_text(CLASS_XML_TPL.format(name="tmp.cls2"))

    