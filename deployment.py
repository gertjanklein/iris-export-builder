
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


def append_export_notes(config, repo, root:etree.Element):
    now = datetime.datetime.utcnow()
    
    # Local time, space separator between date and time
    utc_ts = now.isoformat(sep=' ', timespec="seconds")
    
    now = now.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
    local_ts = now.isoformat(sep=' ',timespec="seconds")[:19]

    # Assemble a document name and minimal deployment notes
    docname = f"EnsExportProduction_{local_ts.replace(':','-')}"
    if config.Source.type == 'github':
        source = f"""GitHub tag '{config.GitHub.tag}'"""
        notes = f"""<Line num="1">Created from GitHub tag '{config.GitHub.tag}' at {utc_ts} UTC.</Line>"""
    else:
        source = f"""checkout directory '{repo.name}'"""
        notes = f"""<Line num="1">Created from checkout directory '{repo.name}' at {utc_ts} UTC.</Line>"""
    machine = platform.node()

    # Add names of embedded items
    items, projectitems = [], []
    for i, item in enumerate(repo.src_items):
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
    
    # Add the name of the deployment to the project
    projectitems.append(f'<ProjectItem name="EnsExportNotes.{docname}.PTD" type="PTD"></ProjectItem>')

    # Create and add project to deployment
    projectitems = '\n'.join(projectitems)
    data = PROJECT_TPL.format(name=docname, local_ts=local_ts, utc_ts=utc_ts, source=source, items=projectitems)
    el = etree.fromstring(data)
    el.tail = '\n\n'
    root.append(el)
    
    # Create and add deployment notes to deployment
    items = '\n'.join(items)
    data = DPL_NOTES_TPL.format(docname=docname, machine=machine, utc=utc_ts, notes=notes, items=items)
    parser = etree.XMLParser(strip_cdata=False)
    el = etree.fromstring(data, parser=parser)
    el.tail = '\n\n'
    root.append(el)

