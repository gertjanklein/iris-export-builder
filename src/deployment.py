
import datetime
import platform

from lxml import etree

import namespace as ns


# Template for project embedded in deployment
PROJECT_TPL = """
<Project name="{name}" LastModified="{local_ts}">
<ProjectDescription>Studio Project generated from {source} at {utc_ts} UTC</ProjectDescription>
<Items>
{items}
</Items>
</Project>
"""

# Template for deployment notes embedded in deployment
DPL_NOTES_TPL = """
<Document name="EnsExportNotes.{docname}.PTD">
<ProjectTextDocument name="EnsExportNotes.{docname}" description="Export Notes for export {docname}">
<![CDATA[<Deployment>
<Creation>
<Machine>{machine}</Machine>
<Instance></Instance>
<Namespace></Namespace>
<SourceProduction></SourceProduction>
<Username></Username>
<UTC>{utc}</UTC>
</Creation>
<Notes>{notes}</Notes>
<Contents>
<ExportProject></ExportProject>
{items}
</Contents>
<ProductionClassInExport></ProductionClassInExport>
</Deployment>
]]></ProjectTextDocument>
</Document>
"""


def add_deployment(config:ns.Namespace, name:str, root:etree.Element):

    # Get descriptions of items for export notes and Studio project
    items, projectitems = get_items_xml(name, root)

    # Get current timestamp in UTC and local time
    utc_ts, local_ts = get_timestamps()

    # Assemble a document name and minimal deployment notes
    docname = f"EnsExportProduction_{local_ts.replace(':','-')}"
    if config.Source.type == 'github':
        source = f"""GitHub tag '{config.GitHub.tag}'"""
        notes = f"""<Line num="1">Created from GitHub tag '{config.GitHub.tag}' at {utc_ts} UTC.</Line>"""
    else:
        source = f"""checkout directory '{name}'"""
        notes = f"""<Line num="1">Created from checkout directory '{name}' at {utc_ts} UTC.</Line>"""
    machine = platform.node()

    # Add the name of the deployment to the project
    projectitems.append(f'<ProjectItem name="EnsExportNotes.{docname}.PTD" type="PTD"></ProjectItem>')

    # Create project element
    itemstxt = '\n'.join(projectitems)
    data = PROJECT_TPL.format(name=docname, local_ts=local_ts, utc_ts=utc_ts, source=source, items=itemstxt)
    el = etree.fromstring(data)
    el.tail = '\n\n'
    root.append(el)
    
    # Create deployment notes element
    itemstxt = '\n'.join(items)
    data = DPL_NOTES_TPL.format(docname=docname, machine=machine, utc=utc_ts, notes=notes, items=itemstxt)
    parser = etree.XMLParser(strip_cdata=False)
    el = etree.fromstring(data, parser=parser)
    el.tail = '\n\n'
    root.append(el)


def get_timestamps():
    """Returns UTC and local time in IRIS timestamp format"""

    now = datetime.datetime.utcnow()
    utc_ts = now.isoformat(sep=' ', timespec="seconds")
    now = now.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
    local_ts = now.isoformat(sep=' ', timespec="seconds")[:19]

    return utc_ts, local_ts


def get_items_xml(name:str, root:etree.Element):

    items, projectitems = [], []
    
    for i, el in enumerate(root):
        tag = el.tag
        name = el.attrib['name']

        if tag == 'Class':
            itemtype = 'cls'
        elif tag == 'Routine':
            itemtype = el.attrib['type'] 
        elif tag == 'Document':
            name, itemtype = name.rsplit('.', 1)
        else:
            raise ValueError(f"Don't know how to handle tag '{tag}' in export.")
        
        # Some IRIS code expects uppercase
        itemtype = itemtype.upper()

        # Add to list of items in export notes
        items.append(f'<Item num="{i+1}">{name}.{itemtype}</Item>')

        if itemtype in ('INC', 'INT'):
            # For Studio projects, the item type of include files etc is MAC.
            # The actual type is then part of the name.
            name = f"{name}.{itemtype}"
            itemtype = 'MAC'
        elif tag == 'Document':
            name = f"{name}.{itemtype}"
        
        # Add to list of items in Studio project
        projectitems.append(f'<ProjectItem name="{name}" type="{itemtype}"></ProjectItem>')

    return items, projectitems

