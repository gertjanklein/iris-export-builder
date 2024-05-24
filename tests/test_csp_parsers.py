from importlib import import_module
from typing import Any
from io import BytesIO

from lxml import etree

import pytest

from config import ConfigurationError

builder = import_module("build-export") # type: Any


CFG = """
[Source]
type = "directory"
srctype = "xml"
srcdir = 'src'
cspdir = 'csp'
[CSP]
export = 'embed'
[Data]
export = 'embed'
[Directory]
path = '{path}'
[Local]
outfile = 'out.xml'
loglevel = 'debug'
"""


@pytest.mark.usefixtures("reload_modules")
def test_csp_default(src_tree, tmp_path, get_build):
    """ Tests default CSP parser. """

    parsers = "[[CSP.parsers]]\n" \
        "regex = '((/csp)?/[^/]+)/(.+)'\n" \
        "app = '\\1'\n" \
        "item = '\\3'\n" \
        "nomatch = 'error'"
    cfg = CFG.format(path=src_tree) + '\n' + parsers
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'

    assert tree.find('./CSP[@name="hello.csp"][@application="/app"]') is not None, \
        "hello.csp not in export"
    assert tree.find('./CSP[@name="goodbye.csp"][@application="/app"]') is not None, \
        "goodbye.csp not in export"
    
    assert tree.find('./CSP[@name="hello2.csp"][@application="/app2"]') is not None, \
        "hello2.csp not in export"
    assert tree.find('./CSP[@name="goodbye2.csp"][@application="/app2"]') is not None, \
        "goodbye2.csp not in export"


@pytest.mark.usefixtures("reload_modules")
def test_csp_merge_app(src_tree, tmp_path, get_build):
    """ Tests merging application paths CSP parser. """

    parsers = "[[CSP.parsers]]\n" \
        "regex = '((/csp)?/[^/]+)/(.+)'\n" \
        "app = '/app'\n" \
        "item = '\\3'\n" \
        "nomatch = 'error'"
    cfg = CFG.format(path=src_tree) + '\n' + parsers
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'

    assert tree.find('./CSP[@name="hello.csp"][@application="/app"]') is not None, \
        "hello.csp not in export"
    assert tree.find('./CSP[@name="goodbye.csp"][@application="/app"]') is not None, \
        "goodbye.csp not in export"
    
    assert tree.find('./CSP[@name="hello2.csp"][@application="/app"]') is not None, \
        "hello2.csp not in export"
    assert tree.find('./CSP[@name="goodbye2.csp"][@application="/app"]') is not None, \
        "goodbye2.csp not in export"


@pytest.mark.usefixtures("reload_modules")
def test_no_match_raises(src_tree, tmp_path, get_build):
    """ Tests raising an error on non-matching path. """

    parsers = "[[CSP.parsers]]\n" \
        "regex = '((/csp)?/app)/(.+)'\n" \
        "app = '/app'\n" \
        "item = '\\3'\n" \
        "nomatch = 'error'"
    cfg = CFG.format(path=src_tree) + '\n' + parsers
    
    with pytest.raises(ConfigurationError) as e:
        get_build(cfg, tmp_path)
    assert "does not match regex in parser 1" in e.value.args[0], \
        f"Unexpected error message {e.value.args[0]}"


@pytest.mark.usefixtures("reload_modules")
def test_no_match_skips(src_tree, tmp_path, get_build):
    """ Tests skipping items on non-matching path. """

    parsers = "[[CSP.parsers]]\n" \
        "regex = '((/csp)?/app)/(.+)'\n" \
        "app = '/app'\n" \
        "item = '\\3'\n" \
        "nomatch = 'skip'"
    cfg = CFG.format(path=src_tree) + '\n' + parsers
    
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'
    
    assert tree.find('./CSP[@name="hello.csp"][@application="/app"]') is not None, \
        "hello.csp not in export"
    assert tree.find('./CSP[@name="goodbye.csp"][@application="/app"]') is not None, \
        "goodbye.csp not in export"
    
    assert tree.find('./CSP[@name="hello2.csp"][@application="/app"]') is None, \
        "hello2.csp in export"
    assert tree.find('./CSP[@name="goodbye2.csp"][@application="/app"]') is None, \
        "goodbye2.csp in export"

    file = tmp_path / 'cfg.log'
    assert "does not match regex in parser 1" in file.read_text(), "No skip warning in log"


@pytest.mark.usefixtures("reload_modules")
def test_app_leading_slash(src_tree, tmp_path, get_build):
    """ Tests raising an error on missing leading slash. """

    parsers = "[[CSP.parsers]]\n" \
        "regex = '(.+)'\n" \
        "item = '\\1'\n" \
        "nomatch = 'skip'\n"
    
    cfg = CFG.format(path=src_tree) + '\n' + parsers + "app = 'app'"
    with pytest.raises(ValueError) as e:
        get_build(cfg, tmp_path)
    assert "must start with a slash" in e.value.args[0], \
        f"Unexpected error message {e.value.args[0]}"


@pytest.mark.usefixtures("reload_modules")
def test_app_trailing_slash(src_tree, tmp_path, get_build):
    """ Tests raising an error on trailing slash. """

    parsers = "[[CSP.parsers]]\n" \
        "regex = '(.+)'\n" \
        "item = '\\1'\n" \
        "nomatch = 'skip'\n"
    
    cfg = CFG.format(path=src_tree) + '\n' + parsers + "app = '/app/'"
    with pytest.raises(ValueError) as e:
        get_build(cfg, tmp_path)
    assert "must not end with a slash" in e.value.args[0], \
        f"Unexpected error message {e.value.args[0]}"


@pytest.mark.usefixtures("reload_modules")
def test_page_leading_slash(src_tree, tmp_path, get_build):
    """ Tests raising an error on leading slash in item. """

    parsers = "[[CSP.parsers]]\n" \
        "regex = '(.+)'\n" \
        "app = '/app'\n" \
        "nomatch = 'skip'\n"
    
    cfg = CFG.format(path=src_tree) + '\n' + parsers + "item = '/item.csp'"
    with pytest.raises(ValueError) as e:
        get_build(cfg, tmp_path)
    assert "must not start with a slash" in e.value.args[0], \
        f"Unexpected error message {e.value.args[0]}"


@pytest.mark.usefixtures("reload_modules")
def test_page_trailing_slash(src_tree, tmp_path, get_build):
    """ Tests raising an error on trailing slash in item. """

    parsers = "[[CSP.parsers]]\n" \
        "regex = '(.+)'\n" \
        "app = '/app'\n" \
        "nomatch = 'skip'\n"
    
    cfg = CFG.format(path=src_tree) + '\n' + parsers + "item = 'item.csp/'"
    with pytest.raises(ValueError) as e:
        get_build(cfg, tmp_path)
    assert "must not end with a slash" in e.value.args[0], \
        f"Unexpected error message {e.value.args[0]}"

