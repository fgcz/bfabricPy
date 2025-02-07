import cyclopts

from bfabric_scripts.cli.workunit.export_definition import export_definition
from bfabric_scripts.cli.workunit.not_available import (
    list_not_available_proteomics_workunits,
)

app = cyclopts.App()
app.command(list_not_available_proteomics_workunits, name="not-available")
app.command(export_definition, name="export-definition")
