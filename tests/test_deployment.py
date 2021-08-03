""" Tests helpers in deployment code.
"""

from lxml import etree
import pytest

import deployment


def test_unknown_element():
    """ Tests unknown element raises an error """

    root = etree.Element('Export')

    # These should be known
    el = etree.Element('Class')
    el.attrib['name'] = 'name'
    root.append(el)
    el = etree.Element('Routine')
    el.attrib['name'] = 'name'
    el.attrib['type'] = 'MAC'
    root.append(el)
    el = etree.Element('Document')
    el.attrib['name'] = 'name.PTD'
    root.append(el)

    # ... so this should not raise an error
    result = deployment.get_items_xml('joop', root)
    assert len(result) == 2, f"Unexpected result: {result}"

    # This element is unknown
    el = etree.Element('SomethingElse')
    el.attrib['name'] = 'something'
    root.append(el)

    # ... and therefore should raise an error
    with pytest.raises(ValueError) as e:
        result = deployment.get_items_xml('joop', root)
    msg = e.value.args[0]
    assert msg == "Don't know how to handle tag 'SomethingElse' in export."

