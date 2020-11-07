from importlib import import_module
from io import BytesIO
from typing import Any
from os.path import dirname, join, exists

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
srcdir = '{srcdir}'
[GitHub]
user = "intersystems-community"
repo = "iris-rest-api-template"
tag = "22802745711e276121f81374aba8d17ddcd23d83"
[Local]
outfile = 'out.xml'
"""


def get_credentials():
    name = join(dirname(__file__), 'server.toml')
    if not exists:
        return ''
    with open(name) as f:
        svr = f.read()
    return svr
SVR = get_credentials()


@pytest.mark.skipif(SVR=='', reason="No UDL-XML conversion server configured.")
@pytest.mark.usefixtures("reload_modules")
def test_subpath_all(tmp_path, get_build):
    """Baseline test for simple GitHub download.
    
    Checks that all expected classes are there."""

    cfg = CFG.format(srcdir='src') + "\n" + SVR
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('/Class[@name="dc.Sample.Person"]') is not None, "dc.Sample.Person not in export"
    assert tree.find('/Class[@name="Sample.REST.Base"]') is not None, "Sample.REST.Base not in export"

@pytest.mark.skipif(SVR=='', reason="No UDL-XML conversion server configured.")
@pytest.mark.usefixtures("reload_modules")
def test_subpath(tmp_path, get_build):
    """Tests specifying a source subpath.

    Sources not in that path should not be present in the export."""
    
    cfg = CFG.format(srcdir='src/dc/Sample/REST') + "\n" + SVR
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('/Class[@name="dc.Sample.Person"]') is None, "dc.Sample.Person in export"
    assert tree.find('/Class[@name="Sample.REST.Base"]') is not None, "Sample.REST.Base not in export"

