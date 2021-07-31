
import datetime
import platform

from lxml import etree


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


def get_deployment_items(config, repo) -> list[etree.Element]:

    results = []

    # Get current timestamp in UTC and local time
    utc_ts, local_ts = get_timestamps()

    # Assemble a document name and minimal deployment notes
    docname = f"EnsExportProduction_{local_ts.replace(':','-')}"
    if config.Source.type == 'github':
        source = f"""GitHub tag '{config.GitHub.tag}'"""
        notes = f"""<Line num="1">Created from GitHub tag '{config.GitHub.tag}' at {utc_ts} UTC.</Line>"""
    else:
        source = f"""checkout directory '{repo.name}'"""
        notes = f"""<Line num="1">Created from checkout directory '{repo.name}' at {utc_ts} UTC.</Line>"""
    machine = platform.node()

    # Get names of embedded items
    items, projectitems = get_items_xml(config, repo.src_items)
    
    # Add the name of the deployment to the project
    projectitems.append(f'<ProjectItem name="EnsExportNotes.{docname}.PTD" type="PTD"></ProjectItem>')

    # Create project element
    itemstxt = '\n'.join(projectitems)
    data = PROJECT_TPL.format(name=docname, local_ts=local_ts, utc_ts=utc_ts, source=source, items=itemstxt)
    el = etree.fromstring(data)
    el.tail = '\n\n'
    results.append(el)
    
    # Create deployment notes element
    itemstxt = '\n'.join(items)
    data = DPL_NOTES_TPL.format(docname=docname, machine=machine, utc=utc_ts, notes=notes, items=itemstxt)
    parser = etree.XMLParser(strip_cdata=False)
    el = etree.fromstring(data, parser=parser)
    el.tail = '\n\n'
    results.append(el)

    return results


def get_timestamps():
    """Returns UTC and local time in IRIS timestamp format"""

    now = datetime.datetime.utcnow()
    utc_ts = now.isoformat(sep=' ', timespec="seconds")
    now = now.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
    local_ts = now.isoformat(sep=' ', timespec="seconds")[:19]

    return utc_ts, local_ts


def get_items_xml(config, repo_items:list):

    items, projectitems = [], []
    for i, item in enumerate(repo_items):
        basename, itemtype = item.name.rsplit('.', 1)
        # Remove xml suffix, if present
        if config.Source.srctype == 'xml' and itemtype.lower() == 'xml':
            basename, itemtype = basename.rsplit('.', 1)
        itemtype = itemtype.upper()
        items.append(f'<Item num="{i+1}">{basename}.{itemtype}</Item>')
        if itemtype in ('INC', 'INT'):
            # For Studio projects, the item type of include files etc is MAC.
            # The actual type is then part of the name.
            basename = f"{basename}.{itemtype}"
            itemtype = 'MAC'
        projectitems.append(f'<ProjectItem name="{basename}" type="{itemtype}"></ProjectItem>')
    return items, projectitems


