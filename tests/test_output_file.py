""" Tests output file handling.
"""

from importlib import import_module
from typing import Any
from os.path import join
from unittest.mock import patch

import pytest

builder = import_module("build-export") # type: Any


CFG = """
[Source]
type = "directory"
srctype = 'xml'
cspdir = 'csp'
datadir = 'data'
srcdir = 'src'
[CSP]
export = 'none'
[Data]
export = 'none'
[Directory]
path = '{path}'
[Local]
"""


@pytest.mark.usefixtures("reload_modules")
def test_unknown_replacement(src_tree, tmp_path):
    """ Tests log warning for unknown replacement
    """
 
    # Create configuration
    toml = CFG.format(path=src_tree, cspdir='csp')
    toml += "outfile = 'out{replaceme}.xml'"

    # Write to file
    cfgfile = str(tmp_path / 'cfg.toml')
    with open(cfgfile, 'wt') as f:
        f.write(toml)
    
    # Create export
    args = ['builder', cfgfile, '--no-gui']
    with patch('sys.argv', args):
        builder.main()

    # Make sure warning present in log file
    log = tmp_path / 'cfg.log'
    text = log.read_text()
    assert "ignoring unrecognized replacement in outfile" in text, f"Unexpected log message {text}"

    # Make sure output file has replacement string as-is
    out = tmp_path / 'out{replaceme}.xml'
    assert out.exists(), "Output filename doesn't have unaltered replacement string"


@pytest.mark.usefixtures("reload_modules")
def test_create_output_dir(src_tree, tmp_path):
    """ Tests that output directory is created automatically
    """
 
    # Create configuration
    toml = CFG.format(path=src_tree, cspdir='csp')
    subpath = join('subpath', 'out.xml')
    toml = f"{toml}\noutfile='{subpath}'\n"

    # Write to file
    cfgfile = str(tmp_path / 'cfg.toml')
    with open(cfgfile, 'wt') as f:
        f.write(toml)
    
    # Create export
    args = ['builder', cfgfile, '--no-gui']
    with patch('sys.argv', args):
        builder.main()

    # Make sure output file has replacement string as-is
    out = tmp_path / 'subpath' / 'out.xml'
    assert out.exists(), "Output file not in subpath"




