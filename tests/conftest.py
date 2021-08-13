from typing import Any

import sys
from importlib import reload, import_module
from unittest.mock import patch
import os
from os.path import dirname, join, exists, relpath
from io import BytesIO
import zipfile
import logging
from pathlib import Path

from lxml import etree
import requests
from requests.exceptions import RequestException

import pytest
import docker

import config
builder = import_module("build-export") # type: Any



@pytest.fixture(scope="function")
def reload_modules():
    """Reload modules to clear state for new test."""

    # Reload after running the test
    yield
    # Close any handlers in the logging module
    builder.cleanup_logging()
    reload(sys.modules['logging'])
    reload(sys.modules['config'])
    reload(sys.modules['build-export'])


@pytest.fixture
def get_config():
    def get_config(toml:str, tmp_path:Path):
        """ Returns a namespace for a TOML in a string """

        cfgfile = str(tmp_path / 'cfg.toml')
        with open(cfgfile, 'wt') as f:
            f.write(toml)
        
        args = ['builder', cfgfile, '--no-gui']
        with patch('sys.argv', args):
            cfg = config.get_config()
        
        return cfg

    return get_config


@pytest.fixture
def get_build():
    def get_build(toml:str, tmp_path):
        """Retrieves a build using the toml config passed in."""
        
        cfgfile = str(tmp_path / 'cfg.toml')
        with open(cfgfile, 'wt') as f:
            f.write(toml)
        
        args = ['builder', cfgfile, '--no-gui']
        with patch('sys.argv', args):
            builder.main()
        
        outfile = str(tmp_path / 'out.xml')
        with open(outfile, 'rb') as bf:
            export = bf.read()

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
            builder.main()
        
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
            return
        tree = etree.parse(BytesIO(export))
        with open(schema_filename, encoding='UTF-8') as f:
            schema = etree.XMLSchema(etree.parse(f))
        valid = schema.validate(tree)
        # pylint: disable=no-member
        assert valid, f"Export schema validation failed: {schema.error_log.last_error}"
    return validate_schema


# ===== UDL -> XML convertor in docker

def _open_local():
    """ Returns the contents of server.toml, if present """

    name = join(dirname(__file__), 'server.toml')
    if not exists(name):
        return None
    with open(name) as f:
        return f.read()

def docker_available():
    """ Checks whether Docker is available """

    try:
        client = docker.from_env()
        return True
    except docker.errors.DockerException:
        return False


if _server_toml := _open_local():
    # A local toml server definition is available; use that
    @pytest.fixture(scope="session")
    def server_toml():
        return _server_toml

elif not docker_available():
    # Docker unavailable; return None to indicate no server available
    @pytest.fixture(scope="session")
    def server_toml():
        return None

else:
    # Docker available; spin up a temporary IRIS
    @pytest.fixture(scope="session")
    def server_toml(iris_service):
        ip, port = iris_service
        toml = f"[Server]\nhost='{ip}'\nport='{port}'\n" \
            "username='_SYSTEM'\npassword='SYS'\n"
        return toml


@pytest.fixture(scope="session")
def iris_service(docker_ip, docker_services):
    """Ensure that HTTP service is up and responsive."""

    port = docker_services.port_for("iris_udl_to_xml", 52773)
    url = "http://{}:{}/api/atelier/".format(docker_ip, port)
    docker_services.wait_until_responsive(
        timeout=120.0, pause=0.5, check=lambda: is_responsive(url)
    )

    return docker_ip, port


def is_responsive(url):
    """ Helper method, waits until an http URL is available """

    try:
        response = requests.get(url, auth=('_SYSTEM','SYS'), timeout=1)
        if response.status_code == 200:
            return True
    except RequestException:
        pass
    
    return False


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """ Override to specify where docker-compose.yml is """
    
    return join(pytestconfig.rootdir, "docker", "docker-compose.yml")


# ===== Create a source file tree for testing

# Class export template (XML)
CLS_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Class name="{name}">
<Description>Non-latin: €ş.</Description>
<Super>%RegisteredObject</Super>
</Class>
</Export>
"""

INC_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Routine name="Include" type="INC"><![CDATA[
#define Hello "World €ş."
]]></Routine>
</Export>
"""

# CSP file template
CSP_TPL = """\
<!DOCTYPE html>
<html>
<head><title>{name}</title></head>
<body>
<h1>{name}</h1>
Non-latin: €ş.
</body>
</html>
"""

# Lookup table export template
LUT_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Document name="{name}.LUT">
<lookupTable>
<entry table="{name}" key="test_key">Non-latin: €ş.</entry>
</lookupTable>
</Document>
</Export>
"""

# Ensemble system default settings export template
ESD_TPL = """\
<?xml version='1.0' encoding='UTF-8'?>
<Export generator="IRIS" version="26">
<Document name="Ens.Config.DefaultSettings.esd">
<defaultSettings>
<item production="*" item="Test" class="*" setting="Test" value="Non-latin: €ş."><Deployable>true</Deployable></item>
</defaultSettings>
</Document>
</Export>
"""


@pytest.fixture(scope="session")
def src_tree(tmp_path_factory):
    """ Creates a source tree with items of all types.

    Used in all tests in this module. Returns the base directory
    for the source tree.
    """
    # Create a base temp directory for this module
    base = tmp_path_factory.mktemp("basic_source_tree", numbered=False) # type: Path
    
    # Two classes directly in the root of the source dir
    dir = base / 'src'
    dir.mkdir(parents=True)
    for name in 'a', 'b':
        file = dir / f"{name}.cls.xml"
        file.write_text(CLS_TPL.format(name=f"tmp.{name}"), encoding='UTF-8')
    
    # A class one level deeper
    dir = base / 'src' / 'c'
    dir.mkdir(parents=True)
    file = dir / "cc.cls.xml"
    contents = CLS_TPL.format(name="tmp.c.cc")
    timestamps = '<TimeCreated>65958,79762.139</TimeCreated>\n' \
        '<TimeChanged>65958,79762.139</TimeChanged>\n'
    idx = contents.find('<Desc')
    contents = contents[:idx] + timestamps + contents[idx:]
    file.write_text(contents, encoding='UTF-8')
    
    # An include file
    dir = base / 'src'
    file = dir / "Include.inc.xml"
    file.write_text(INC_TPL, encoding='UTF-8')
    
    # Two csp files under application directory /app
    dir = base / 'csp' / 'app'
    dir.mkdir(parents=True)
    for name in 'hello', 'goodbye':
        file = dir / f"{name}.csp"
        file.write_text(CSP_TPL.format(name=name), encoding='UTF-8')
    
    # A binary-type CSP file (does not need actual 'binary' data)
    file = dir / "binary.bin"
    file.write_text('abc')

    # A typeless CSP file, should be interpreted as binary
    file = dir / "dat"
    file.write_text('abc')

    # Two more CSP files in a different application
    dir = base / 'csp' / 'app2'
    dir.mkdir(parents=True)
    for name in 'hello2', 'goodbye2':
        file = dir / f"{name}.csp"
        file.write_text(CSP_TPL.format(name=name), encoding='UTF-8')

    # Data dir
    dir = base / 'data'
    dir.mkdir(parents=True)

    # ... with a lookup table
    file = dir / "Test.lut.xml"
    file.write_text(LUT_TPL.format(name="Test"), encoding='UTF-8')

    # ... and a systems default settings export
    file = dir / "Settings.esd.xml"
    file.write_text(ESD_TPL, encoding='UTF-8')

    return base


@pytest.fixture(scope="session")
def src_tree_zipped(src_tree:Path):
    """Returns the source tree in a zipfile."""

    parent = str(src_tree.parent)

    # We don't need an actual file
    data = BytesIO()
    with zipfile.ZipFile(data, mode='w') as zip:
        for dirpath, _, filenames in os.walk(src_tree):
            # Add directory entry
            zip.write(dirpath, relpath(dirpath, parent))
            # Add files in this directory
            for filename in filenames:
                full_path = join(dirpath, filename)
                relative_path = relpath(full_path, parent)
                zip.write(full_path, relative_path)
    
    # Save to file for debugging
    data.seek(0)
    with open(join(src_tree, '..', 'src_tree_zipped.zip'), 'wb') as f:
        f.write(data.read())
    
    # Rewind the stream and create a new ZipFile object from it
    data.seek(0)
    zip = zipfile.ZipFile(data)
    
    return zip

