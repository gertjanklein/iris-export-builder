from importlib import import_module
import binascii

from typing import Any

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
    
    cfg = CFG.format(deployment='false') + "\nthreads=1\n" + server_toml
    export = get_build(cfg, tmpdir)
    validate_schema(export)
    # Check binary equality
    crc = binascii.crc32(export)
    assert crc == 663428536
    


