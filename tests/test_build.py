from unittest.mock import patch
import importlib
import binascii
import logging

import config
builder = importlib.import_module("build-export")


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
"""


def test_build(tmpdir):
    cfgfile = str(tmpdir.join('cfg.toml'))
    with open(cfgfile, 'wt') as f:
        f.write(CFG)
    
    args = ['builder', cfgfile, '--no-gui']
    with patch('sys.argv', args):
        cfg = config.get_config()
    builder.run(cfg)
    
    outfile = str(tmpdir.join('out.xml'))
    with open(outfile, 'rb') as f:
        export = f.read()
    
    crc = binascii.crc32(export)
    assert crc == 1384993019
    
    # Cleanup: log handler still has log file open
    logging.getLogger().handlers.clear()
    tmpdir.join('..').remove(ignore_errors=True)
        