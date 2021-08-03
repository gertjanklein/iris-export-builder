""" Tests loading a token from an external file.
"""

from pathlib import Path

import pytest

from config import ConfigurationError
import namespace as ns


# Basic configuration for the tests in this module
CFG = """
[Source]
type = "github"
[GitHub]
user = 'x'
repo = 'x'
tag = 'x'
token = '{token}'
[Local]
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_token_embedded(tmp_path:Path, get_config):
    """ Tests token directyly in configuration """

    cfg = CFG.format(token='abc')
    config = get_config(cfg, tmp_path) # type: ns.Namespace
    assert 'GitHub' in config, "No Server section"
    gh = config.GitHub
    assert isinstance(gh, ns.Namespace), "GitHub not a section"
    assert gh.token == 'abc', f"Token has unexpected value: '{gh.token}'"


@pytest.mark.usefixtures("reload_modules")
def test_token_external_no_nl(tmp_path:Path, get_config):
    """ Tests token from external file """

    ext = tmp_path / 'token.txt'
    with open(ext, 'wt') as f:
        f.write('def')

    cfg = CFG.format(token=f"@{ext}")
    config = get_config(cfg, tmp_path) # type: ns.Namespace
    assert 'GitHub' in config, "No Server section"
    gh = config.GitHub
    assert isinstance(gh, ns.Namespace), "GitHub not a section"
    assert gh.token == 'def', f"Token has unexpected value: '{gh.token}'"


@pytest.mark.usefixtures("reload_modules")
def test_token_external_with_nl(tmp_path:Path, get_config):
    """ Tests token from external file """

    ext = tmp_path / 'token.txt'
    with open(ext, 'wt') as f:
        f.write('ghi\n\n\n')

    cfg = CFG.format(token=f"@{ext}")
    config = get_config(cfg, tmp_path) # type: ns.Namespace
    assert 'GitHub' in config, "No Server section"
    gh = config.GitHub
    assert isinstance(gh, ns.Namespace), "GitHub not a section"
    assert gh.token == 'ghi', f"Token has unexpected value: '{gh.token}'"


@pytest.mark.usefixtures("reload_modules")
def test_token_relative(tmp_path:Path, get_config):
    """ Tests token from external file, relative path """

    ext = tmp_path / 'token.txt'
    with open(ext, 'wt') as f:
        f.write('jkl\n')

    cfg = CFG.format(token="@token.txt")
    config = get_config(cfg, tmp_path) # type: ns.Namespace
    assert 'GitHub' in config, "No Server section"
    gh = config.GitHub
    assert isinstance(gh, ns.Namespace), "GitHub not a section"
    assert gh.token == 'jkl', f"Token has unexpected value: '{gh.token}'"


@pytest.mark.usefixtures("reload_modules")
def test_tokenfile_missing(tmp_path:Path, get_config):
    """ Tests token from external file, relative path """

    cfg = CFG.format(token="@missing.txt")
    with pytest.raises(ConfigurationError) as e:
        config = get_config(cfg, tmp_path) # type: ns.Namespace
    assert e.value.args[0].startswith("Error reading token file")

