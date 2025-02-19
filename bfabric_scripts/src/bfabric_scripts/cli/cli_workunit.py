import cyclopts

from bfabric_scripts.cli.workunit.export_definition import cmd_workunit_export_definition
from bfabric_scripts.cli.workunit.not_available import (
    cmd_workunit_not_available,
)

cmd_workunit = cyclopts.App(help="Read workunit entities in B-Fabric.")
cmd_workunit.command(cmd_workunit_not_available, name="not-available")
cmd_workunit.command(cmd_workunit_export_definition, name="export-definition")
