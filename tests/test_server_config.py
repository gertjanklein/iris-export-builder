""" Tests configuration of the UDL -> XML conversion server.
"""

from pathlib import Path

import pytest

import namespace as ns


# Basic configuration for the tests in this module
CFG = """
[Source]
type = "directory"
[Directory]
path = '.'
[Local]
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_defaults(tmp_path, get_config):
    """ Tests default values in Server section """

    cfg = get_config(CFG, tmp_path) # type: ns.Namespace
    assert 'Server' in cfg, "No Server section"
    svr = cfg.Server
    assert isinstance(svr, ns.Namespace), "Server not a section"

    assert svr.host == 'localhost', f"Unexpected value for host: {svr.host}"
    assert svr.port == '52773', f"Unexpected value for host: {svr.port}"
    assert svr.user == 'SuperUser', f"Unexpected value for host: {svr.user}"
    assert svr.password == 'SYS', f"Unexpected value for host: {svr.password}"
    assert svr.namespace == 'USER', f"Unexpected value for host: {svr.namespace}"
    assert svr.https is False, f"Unexpected value for host: {svr.https}"


@pytest.mark.usefixtures("reload_modules")
def test_partial_defaults(tmp_path, get_config):
    """ Tests overriding part of the defaults """

    # Override a few settings
    override = "[Server]\nuser='aap'\npassword='noot'"

    cfg = get_config(f"{CFG}\n{override}", tmp_path) # type: ns.Namespace
    assert 'Server' in cfg, "No Server section"
    svr = cfg.Server
    assert isinstance(svr, ns.Namespace), "Server not a section"

    assert svr.host == 'localhost', f"Unexpected value for host: {svr.host}"
    assert svr.port == '52773', f"Unexpected value for port: {svr.port}"
    assert svr.user == 'aap', f"Unexpected value for user: {svr.user}"
    assert svr.password == 'noot', f"Unexpected value for password: {svr.password}"
    assert svr.namespace == 'USER', f"Unexpected value for namespace: {svr.namespace}"
    assert svr.https is False, f"Unexpected value for https: {svr.https}"


@pytest.mark.usefixtures("reload_modules")
def test_external_def_all(tmp_path:Path, get_config):
    """ Tests overriding server with external file """

    extdef = tmp_path / 'svr.toml'
    settings = "[Server]\n" \
        "host = '127.0.0.1'\n" \
        "port = '12345'\n" \
        "user = 'Asterix'\n" \
        "password = 'Obelix'\n" \
        "namespace = 'Walhalla'\n" \
        "https = true\n"
        
    with open(extdef, 'wt', encoding='utf8') as f:
        f.write(settings)

    cfg = get_config(f"{CFG}\naugment_from='{extdef}'", tmp_path)
    assert 'Server' in cfg, "No Server section"
    svr = cfg.Server
    assert isinstance(svr, ns.Namespace), "Server not a section"

    assert svr.host == '127.0.0.1', f"Unexpected value for host: {svr.host}"
    assert svr.port == '12345', f"Unexpected value for port: {svr.port}"
    assert svr.user == 'Asterix', f"Unexpected value for user: {svr.user}"
    assert svr.password == 'Obelix', f"Unexpected value for password: {svr.password}"
    assert svr.namespace == 'Walhalla', f"Unexpected value for namespace: {svr.namespace}"
    assert svr.https is True, f"Unexpected value for https: {svr.https}"


@pytest.mark.usefixtures("reload_modules")
def test_external_relative_location(tmp_path:Path, get_config):
    """ Tests specifying relative location """

    dir = tmp_path / 'subdir'
    dir.mkdir(parents=True)

    extdef = dir / 'svr.toml'
    settings = "[Server]\nhost = '127.0.0.1'\n"
    with open(extdef, 'wt', encoding='utf8') as f:
        f.write(settings)

    relpath = extdef.relative_to(tmp_path)
    override = f"augment_from = '{relpath}'"

    cfg = get_config(f"{CFG}\n{override}", tmp_path)
    assert 'Server' in cfg, "No Server section"
    svr = cfg.Server
    assert isinstance(svr, ns.Namespace), "Server not a section"

    assert svr.host == '127.0.0.1', f"Unexpected value for host: {svr.host}"
