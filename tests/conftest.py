import sys
from importlib import reload, import_module
from unittest.mock import patch
import logging
from typing import Any

import pytest

import config
builder = import_module("build-export") # type: Any


@pytest.fixture(scope="function")
def reload_modules():
    """Reload modules to clear state for new test."""

    # Reload after running the test
    yield
    reload(sys.modules['logging'])
    reload(sys.modules['config'])
    reload(sys.modules['build-export'])


@pytest.fixture
def get_build():
    def get_build(toml:str, tmp_path):
        """Retrieves a build using the toml config passed in."""
        
        cfgfile = str(tmp_path / 'cfg.toml')
        with open(cfgfile, 'wt') as f:
            f.write(toml)
        
        args = ['builder', cfgfile, '--no-gui']
        with patch('sys.argv', args):
            cfg = config.get_config()
        builder.run(cfg)
        
        outfile = str(tmp_path / 'out.xml')
        with open(outfile, 'rb') as bf:
            export = bf.read()

        # Cleanup: log handler still has log file open
        for h in logging.getLogger().handlers:
            h.close()
        logging.getLogger().handlers.clear()

        return export
    return get_build
