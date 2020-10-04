from unittest.mock import patch
from importlib import import_module, reload
import binascii
import logging
from os.path import dirname, join, exists
from io import BytesIO, StringIO
from typing import Any

import pytest
import docker

import requests
from requests.exceptions import ConnectionError
from requests.auth import HTTPBasicAuth

from lxml import etree

import config
builder = import_module("build-export") # type: Any


# Check whether docker(-compose) is available
try:
    client = docker.from_env()
    NODOCKER = False
    del client
except docker.errors.DockerException:
    NODOCKER = True


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
[Server]
host = "{host}"
port = "{port}"
[Local]
outfile = 'out.xml'
"""


@pytest.mark.skipif(NODOCKER, reason="Docker not available.")
@pytest.mark.usefixtures("reload_modules")
def test_build(tmpdir, iris):
    """Retrieve and build specific packge."""
    host, port = iris
    cfg = CFG.format(host=host, port=port)
    export = get_build(cfg, tmpdir)
    validate_schema(export, 'irisexport.xsd')
    # Check binary equality
    crc = binascii.crc32(export)
    assert crc == 663428536
    

@pytest.mark.skipif(NODOCKER, reason="Docker not available.")
@pytest.mark.usefixtures("reload_modules")
def test_build_deployment(tmpdir, iris):
    """Check creating deployment."""
    host, port = iris
    cfg = CFG.format(host=host, port=port) + "\ndeployment = true"
    export = get_build(cfg, tmpdir)
    tree = etree.parse(BytesIO(export))
    # Can't CRC file, export notes contain timestamp. Check contents.
    assert tree.docinfo.root_name == 'Export'
    assert tree.find('/Class[@name="Strix.Background.ItemInfo"]') is not None, "Strix.Background.ItemInfo not in export"
    assert tree.find('/Routine[@name="Strix"]') is not None, "Strix.inc not in export"
    assert len(tree.findall('/Project')) == 1, "No project in export"
    assert len(tree.findall('/Project/Items/ProjectItem')) == 24, "Unexpected number of items in export"
    ptd_name = tree.find('/Project/Items/ProjectItem[24]').get('name')
    assert tree.find(f'/Document[@name="{ptd_name}"]') is not None, "Deployment document not in export"
    ptd = tree.find(f'/Document[@name="{ptd_name}"]/ProjectTextDocument')
    assert ptd is not None, "Embedded project text document not in deployment"
    subtree = etree.parse(StringIO(ptd.text))
    assert subtree.find('/Contents') is not None, "No Contents element in deployment"
    assert len(subtree.findall('/Contents/Item')) == 23, "Unexpected number of items in deployment"
    assert subtree.find('/Contents/Item[23]').text == 'Strix.INC', "Unexpected order of items in deployment"
    
    validate_schema(export, 'irisexport.xsd')
    

def validate_schema(export, schema_filename):
    """Validate the export against the schema file, if it exists."""
    
    schema_filename = join(dirname(__file__), schema_filename)
    if not exists(schema_filename):
        return
    tree = etree.parse(BytesIO(export))
    with open(schema_filename, encoding='UTF-8') as f:
        schema = etree.XMLSchema(etree.parse(f))
    valid = schema.validate(tree)
    # pylint: disable=no-member
    assert valid, f"Export schema validation failed: {schema.error_log.last_error}"


# =====

def get_build(toml:str, tmpdir):
    """Retrieves a build using the toml config passed in."""
    
    cfgfile = str(tmpdir.join('cfg.toml'))
    with open(cfgfile, 'wt') as f:
        f.write(toml)
    
    args = ['builder', cfgfile, '--no-gui']
    with patch('sys.argv', args):
        cfg = config.get_config()
    builder.run(cfg)
    
    outfile = str(tmpdir.join('out.xml'))
    with open(outfile, 'rb') as bf:
        export = bf.read()

    # Cleanup: log handler still has log file open
    logging.getLogger().handlers.clear()

    return export


@pytest.fixture(scope="function")
def reload_modules():
    """Reload modules to clear state for new test."""

    # Reload after running the test
    yield
    reload(config)
    reload(builder)
    reload(logging)


@pytest.fixture(scope="session")
def iris(docker_ip, docker_services):
    """Ensure the API is up and responsive."""

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("iris", 52773)
    url = "http://{}:{}/api/atelier/".format(docker_ip, port)

    # Helper: checks whether IRIS API is available
    auth = HTTPBasicAuth('_SYSTEM', 'SYS')
    def is_responsive():
        try:
            response = requests.get(url, auth=auth)
            if response.status_code == 200:
                return True
            raise ValueError(f"Unexpected status code '{response.status_code}'.")
        except ConnectionError:
            return False
        return None

    docker_services.wait_until_responsive(
        timeout=40.0, pause=1, check=is_responsive)
    
    return docker_ip, port


