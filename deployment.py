
import datetime
import platform

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


def append_export_notes(config, repo, outfile):
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
        projectitems.append(f'<ProjectItem name="{basename}" type="{itemtype.upper()}"></ProjectItem>')
        items.append(f'<Item num="{i+1}">{basename}.{itemtype.upper()}</Item>')
    # Add the name of the deployment to the project
    projectitems.append(f'<ProjectItem name="EnsExportNotes.{docname}.PTD" type="PTD"></ProjectItem>')

    # Create and write project to deployment
    projectitems = '\n'.join(projectitems)
    data = PROJECT_TPL.format(name=docname, local_ts=local_ts, utc_ts=utc_ts, source=source, items=projectitems)
    outfile.write(data + '\n\n')
    
    # Create and write deployment notes to deployment
    items = '\n'.join(items)
    data = DPL_NOTES_TPL.format(docname=docname, machine=machine, utc=utc_ts, notes=notes, items=items)
    outfile.write(data + '\n\n')



