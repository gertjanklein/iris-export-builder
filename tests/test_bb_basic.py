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
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_basic(tmpdir, server_toml, get_build, validate_schema):
    """Retrieve and build specific packge."""
    
    if not server_toml:
        pytest.skip("No XML -> UDL server found.")
    
    cfg = CFG.format(deployment='false') + "\nthreads=1\n" + server_toml
    export = get_build(cfg, tmpdir)
    validate_schema(export)
    
