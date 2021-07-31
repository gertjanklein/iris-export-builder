import sys
from importlib import reload, import_module
from unittest.mock import patch
from os.path import dirname, join, exists
from io import BytesIO
import logging

from typing import Any

from lxml import etree
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


@pytest.fixture
def get_build_separate():
    def get_build(toml:str, tmp_path):
        """Retrieves a build using the toml config passed in."""
        
        # Write configuration TOML
        cfgfile = str(tmp_path / 'cfg.toml')
        with open(cfgfile, 'wt') as f:
            f.write(toml)
        
        # Create build (in multiple files)
        args = ['builder', cfgfile, '--no-gui']
        with patch('sys.argv', args):
            cfg = config.get_config()
        builder.run(cfg)
        
        # Get source export
        src_file = str(tmp_path / 'out.xml')
        with open(src_file, 'rb') as bf:
            src_export = bf.read()
        
        # Get CSP export (if it exists)
        csp_file = str(tmp_path / 'out_csp.xml')
        if exists(csp_file):
            with open(csp_file, 'rb') as bf:
                csp_export = bf.read()
        else:
            csp_export = b''
        
        # Get data export (if it exists)
        data_file = str(tmp_path / 'out_data.xml')
        if exists(data_file):
            with open(data_file, 'rb') as bf:
                data_export = bf.read()
        else:
            data_export = b''

        # Cleanup: log handler still has log file open
        for h in logging.getLogger().handlers:
            h.close()
        logging.getLogger().handlers.clear()

        return src_export, csp_export, data_export
        
    return get_build



@pytest.fixture
def validate_schema():
    def validate_schema(export, schema_file='irisexport.xsd'):
        """Validate the export against the schema file, if it exists."""
        
        schema_filename = join(dirname(__file__), schema_file)
        if not exists(schema_filename):
            pytest.skip("No XSD to validate against")
            return
        tree = etree.parse(BytesIO(export))
        with open(schema_filename, encoding='UTF-8') as f:
            schema = etree.XMLSchema(etree.parse(f))
        valid = schema.validate(tree)
        # pylint: disable=no-member
        assert valid, f"Export schema validation failed: {schema.error_log.last_error}"
    return validate_schema

