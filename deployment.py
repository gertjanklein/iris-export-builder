
import datetime
import platform


DPL_NOTES_TPL = """
<Document name="{docname}.PTD">
<ProjectTextDocument name="EnsExportNotes" description="Export notes">
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
</Contents>
<ProductionClassInExport></ProductionClassInExport>
</Deployment>
]]></ProjectTextDocument>
</Document>
"""

def append_export_notes(config, repo, outfile):
    utc = datetime.datetime.utcnow().isoformat(sep=' ',timespec="seconds")
    docname = f"EnsExportNotes.EnsExportProduction_{utc.replace(':','-')}"
    if config.Source.type == 'github':
        notes = f"""<Line num="1">Created from GitHub tag '{config.GitHub.tag}'</Line>'"""
    else:
        notes = f"""<Line num="1">Created from checkout directory {repo.name}</Line>'"""
    machine = platform.node()
    data = DPL_NOTES_TPL.format(docname=docname, machine=machine, utc=utc, notes=notes)
    outfile.write(data + '\n\n')



