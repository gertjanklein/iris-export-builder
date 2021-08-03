import sys
from importlib import reload, import_module
from typing import Any
from io import BytesIO
import re

from lxml import etree

import pytest

builder = import_module("build-export") # type: Any


CFG = """
[Source]
type = "directory"
srctype = "xml"
srcdir = 'src'
cspdir = ''
datadir = ''
skip = ['/csp/*', '/data/*']
[Directory]
path = '{path}'
[Local]
outfile = 'out.xml'
"""


@pytest.mark.usefixtures("reload_modules")
def test_has_timestamps(src_tree, tmp_path, get_build):
    """ Tests creating an export with updated timestamps. """
    
    cfg = CFG.format(path=src_tree) + "\ntimestamps='update'"
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'

    # Regex matching $horolog
    dh = re.compile(r'\d+,\d+(\.\d+)?')
    for el in tree.getroot():
        if el.tag != 'Class':
            continue
        
        # Make sure the TimeCreated element is present and resembles a $Horolog value
        assert el.find('TimeCreated') is not None, "No TimeCreated element in class"
        text = el.find('TimeCreated').text
        assert dh.match(text), f"TimeCreated not in $Horolog format: '{text}'." 
        
        assert el.find('TimeChanged') is not None, "No TimeChanged element in class"
        text = el.find('TimeChanged').text
        assert dh.match(text), f"TimeChanged not in $Horolog format: '{text}'." 


@pytest.mark.usefixtures("reload_modules")
def test_clear_timestamps(src_tree, tmp_path, get_build):
    """ Tests creating an export with removed timestamps. """
    
    cfg = CFG.format(path=src_tree) + "\ntimestamps='clear'"
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'

    for el in tree.getroot():
        if el.tag != 'Class':
            continue
        assert el.find('TimeCreated') is None, "TimeCreated element in class"
        assert el.find('TimeChanged') is None, "TimeChanged element in class"


@pytest.mark.usefixtures("reload_modules")
def test_leave_timestamps(src_tree, tmp_path, get_build):
    """ Tests creating an export with unchanged timestamps. """
    
    cfg = CFG.format(path=src_tree) + "\ntimestamps='leave'"
    export = get_build(cfg, tmp_path)

    tree = etree.parse(BytesIO(export))
    assert tree.docinfo.root_name == 'Export'

    for el in tree.getroot():
        if el.tag != 'Class':
            continue
        
        # Classes a and b had no timestamp and still shouldn't have
        if el.attrib['name'] in ("tmp.a", "tmp.b"):
            assert el.find('TimeCreated') is None, "TimeCreated element in class"
            assert el.find('TimeChanged') is None, "TimeChanged element in class"
        
        # Class c.cc had a timestamp and still should have
        elif el.attrib['name'] in ("tmp.c.cc",):
            assert el.find('TimeCreated') is not None, "No TimeCreated element in class"
            text = el.find('TimeCreated').text
            assert text == '65958,79762.139', f"Unexpected value of TimeCreated: '{text}'." 
            
            assert el.find('TimeChanged') is not None, "No TimeChanged element in class"
            text = el.find('TimeChanged').text
            assert text == '65958,79762.139', f"Unexpected value of TimeCreated: '{text}'." 


@pytest.mark.usefixtures("reload_modules")
def test_empty_is_leave(src_tree, tmp_path, get_build):
    """ Tests creating an export with default timestamps setting. """
    
    cfg = CFG.format(path=src_tree) + "\ntimestamps='leave'"
    export1 = get_build(cfg, tmp_path)

    reload(sys.modules['logging'])
    reload(sys.modules['config'])
    reload(sys.modules['build-export'])

    cfg = CFG.format(path=src_tree)
    export2 = get_build(cfg, tmp_path)

    assert export1 == export2, "Export without setting not same as setting 'leave'"

