
from __future__ import annotations
from typing import Sequence, Optional

from os.path import splitext
import base64

from lxml import etree

import namespace as ns


class Repository:
    """ Represents the collection of items in a repository """

    # Name of the repository: top-level directory in filesystem
    # or zipped version thereof
    name:str

    # The configuration for this run
    config:ns.Namespace

    # Items in this repository
    src_items:Sequence[RepositorySourceItem]
    csp_items:Sequence[RepositoryCspItem]
    data_items:Sequence[RepositoryDataItem]


    def __init__(self, config:ns.Namespace):
        super().__init__() 
        self.config = config

        self.src_items = []
        self.csp_items = []
        self.data_items = []


class RepositoryItem:
    """ Represents an item in a repository """

    # The name of this item
    name:str

    # The type of this item: 'src', 'csp', or 'data'
    kind:str = ''

    # The 'raw' (but decoded) data as stored in the repository
    data:str
    
    # The data wrapped in XML for export (may be the same as data)
    xml:str

    def get_xml(self):
        """ Returns the XML for this item. """
        if hasattr(self, 'xml'):
            return self.xml
        return self.data

    def get_xml_element(self):
        """ Returns an Element object for this item. """
        parser = etree.XMLParser(strip_cdata=False)
        return etree.fromstring(self.get_xml().encode('UTF-8'), parser=parser)
    
    @property
    def horolog(self) -> Optional[str]:
        """ Returns a $horolog-type timestamp for this item, if known. """
        return None
    

class RepositorySourceItem(RepositoryItem):
    kind = 'src'
    
    # Whether the source data is in UDL and hence needs conversion
    is_udl:bool


class RepositoryCspItem(RepositoryItem):
    kind = 'csp'

    # Item- and application name for this CSP item
    csp_name:str
    csp_application:str
    
    @property
    def is_text(self) -> bool:
        """ Whether this item has text contents, as opposed to binary """
        name = self.name
        ext = splitext(name)[1]
        if not ext:
            return False
        ext = ext[1:]
        return ext.lower() in "csp,csr,xml,js,css,xsl,xsd,txt,html".split(',')
    
    
    def get_xml_element(self):
        """ Wraps CSP item in XML export. """
        
        if self.is_text:
            name = 'CSP'
            data = etree.CDATA('\n'+ self.data)
        else:
            name = 'CSPBase64'
            data = b'\n'+ base64.encodebytes(self.data)
        
        export = etree.Element(name)
        export.attrib['name'] = self.csp_name
        export.attrib['application'] = self.csp_application
        export.text = data
        export.tail = '\n\n'

        return export


class RepositoryDataItem(RepositoryItem):
    kind = 'data'


