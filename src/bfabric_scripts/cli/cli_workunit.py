import cyclopts

from bfabric_scripts.cli.workunit.not_available import list_not_available_proteomics_workunits

app = cyclopts.App()
app.command(list_not_available_proteomics_workunits, name="not-available")
