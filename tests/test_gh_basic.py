from importlib import import_module
import binascii
from os.path import dirname, join, exists

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
    validate_schema(export)
    # Check binary equality
    crc = binascii.crc32(export)
    assert crc == 663428536
    


