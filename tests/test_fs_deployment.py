from importlib import import_module
from typing import Any
from io import BytesIO, StringIO

from lxml import etree

import pytest

builder = import_module("build-export") # type: Any


CFG = """
[Source]
type = "directory"
srctype = "xml"
srcdir = 'src'
cspdir = 'csp'
datadir = 'data'
[CSP]
export = 'none'
[Data]
export = 'embed'
[Directory]
path = '{path}'
[Local]
outfile = 'out.xml'
deployment = true
"""


@pytest.mark.usefixtures("reload_modules")
def test_build_deployment(src_tree, tmp_path, get_build, validate_schema):
    """Check creating deployment."""
    
    cfg = CFG.format(path=src_tree)
    export = get_build(cfg, tmp_path)
    tree = etree.parse(BytesIO(export))

    assert tree.docinfo.root_name == 'Export'

    # Basic contents check
    assert tree.find('/Class[@name="tmp.a"]') is not None, \
        "tmp.a not in export"
    assert tree.find('/Routine[@name="Include"][@type="INC"]') is not None, \
        "Routine.inc not in export"
    assert tree.find('/Document[@name="Test.LUT"]') is not None, \
        "Test.LUT not in export"
    assert tree.find('/Document[@name="Ens.Config.DefaultSettings.esd"]') is not None, \
        "Ens.Config.DefaultSettings.esd not in export"

    assert len(tree.findall('/Project')) == 1, "No project in export"

    # Get the names of the items in the Studio project
    names = set()
    project_items = tree.findall('/Project/Items/ProjectItem') 
    for el in project_items:
        name = el.attrib['name']
        typ = el.attrib['type']
        if typ == 'CLS':
            name = f"{name}.{typ}"
        # Normalize type to lowercase
        name, typ = name.rsplit(".", 1)
        name = f"{name}.{typ.lower()}"
        names.add(name)

    # Check the names
    for name in 'tmp.a.cls', 'tmp.b.cls', 'tmp.c.cc.cls', 'Include.inc', \
            'Ens.Config.DefaultSettings.esd', 'Test.lut':
        assert name in names, f"{name} not in Studio project"

    # The project text document is the last entry in the Studio project
    ptd = tree.find(f'/Project/Items/ProjectItem[{len(project_items)}]')
    assert ptd
    ptd_name = ptd.get('name')
    assert tree.find(f'/Document[@name="{ptd_name}"]') is not None, \
        "Deployment document not in export"

    # The contents is a ProjectTextDocument element, embedded as CDATA
    ptd = tree.find(f'/Document[@name="{ptd_name}"]/ProjectTextDocument')
    assert ptd is not None, "Embedded project text document not in deployment"
    subtree = etree.parse(StringIO(ptd.text))
    
    assert subtree.find('/Contents') is not None, "No Contents element in deployment"

    # Check the names in the deployment Contents
    names = set()
    for el in subtree.findall('/Contents/Item'):
        name = el.text
        assert name is not None
        # Normalize type to lowercase
        name, typ = name.rsplit(".", 1)
        name = f"{name}.{typ.lower()}"
        names.add(name)
    
    for name in 'tmp.a.cls', 'tmp.b.cls', 'tmp.c.cc.cls', 'Include.inc', \
            'Ens.Config.DefaultSettings.esd', 'Test.lut':
        assert name in names, f"{name} not in Studio project"
    
    validate_schema(export, 'irisexport.xsd')
