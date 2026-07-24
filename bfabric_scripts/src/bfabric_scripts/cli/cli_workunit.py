import cyclopts

from bfabric_scripts.cli.workunit.diff import cmd_workunit_diff
from bfabric_scripts.cli.workunit.export_definition import cmd_workunit_export_definition
from bfabric_scripts.cli.workunit.not_available import (
    cmd_workunit_not_available,
)
from bfabric_scripts.cli.workunit.upload import cmd_workunit_upload

cmd_workunit = cyclopts.App(help="Read workunit entities in B-Fabric.")
_ = cmd_workunit.command(cmd_workunit_not_available, name="not-available")
_ = cmd_workunit.command(cmd_workunit_export_definition, name="export-definition")
_ = cmd_workunit.command(cmd_workunit_upload, name="upload")
_ = cmd_workunit.command(cmd_workunit_diff, name="diff")
