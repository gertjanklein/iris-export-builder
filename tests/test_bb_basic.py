from os.path import exists
from importlib import import_module

from typing import Any

import pytest

builder = import_module("build-export") # type: Any


CFG = """
[Source]
type = "bitbucket"
srctype = "udl"
srcdir = 'src'
skip = []
[Bitbucket]
owner = "gertjanklein"
repo = "iris-export-builder_test-data"
tag = "main"
[Local]
outfile = '{outfile}'
"""


@pytest.mark.usefixtures("reload_modules")
def test_basic(tmpdir, server_toml, get_build, validate_schema):
    """Retrieve and build specific package."""
    
    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(outfile='out.xml') + server_toml
    export = get_build(cfg, tmpdir)
    validate_schema(export)
    

def test_name_as_tag(tmpdir, server_toml, build):
    """Tests using tag in output file name"""
    
    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(outfile='{tag}.xml') + server_toml
    build(cfg, tmpdir)
    
    assert exists(tmpdir / 'main.xml'), "Output has expected name"
