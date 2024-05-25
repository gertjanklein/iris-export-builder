from importlib import import_module
from io import BytesIO
from typing import Any

from lxml import etree

import pytest

builder = import_module("build-export") # type: Any

# Configuration to retrieve a specific checkin of a
# package from GitHub, and create an export from it.
CFG = """
[Source]
type = "github"
srctype = "udl"
srcdir = '{srcdir}'
[GitHub]
user = "intersystems-community"
repo = "iris-rest-api-template"
tag = "22802745711e276121f81374aba8d17ddcd23d83"
[Local]
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_subpath_all(tmp_path, server_toml, get_build):
    """Baseline test for simple GitHub download.
    
    Checks that all expected classes are there."""

    if not server_toml:
        cfg = CFG.format(srcdir='src') + "converter='builtin'\n"
    else:
        cfg = CFG.format(srcdir='src') + "\n" + server_toml
    
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('./Class[@name="dc.Sample.Person"]') is not None, \
        "dc.Sample.Person not in export"
    assert tree.find('./Class[@name="Sample.REST.Base"]') is not None, \
        "Sample.REST.Base not in export"


@pytest.mark.usefixtures("reload_modules")
def test_subpath(tmp_path, server_toml, get_build):
    """Tests specifying a source subpath.

    Sources not in that path should not be present in the export."""
    
    if not server_toml:
        cfg = CFG.format(srcdir='src/dc/Sample/REST') + "converter='builtin'\n"
    else:
        cfg = CFG.format(srcdir='src/dc/Sample/REST') + "\n" + server_toml
    
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('./Class[@name="dc.Sample.Person"]') is None, \
        "dc.Sample.Person not in export"
    assert tree.find('./Class[@name="Sample.REST.Base"]') is not None, \
        "Sample.REST.Base in export"

