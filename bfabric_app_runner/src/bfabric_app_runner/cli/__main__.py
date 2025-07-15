"""
B-Fabric App Runner - Execute bioinformatics applications on your B-Fabric workunits.

**For automated systems:**
Use ``bfabric-app-runner run workunit`` for end-to-end workunit execution.

**For development and testing:**

1. Create a workunit folder: ``bfabric-app-runner prepare workunit``
2. Navigate to the folder and run ``make help`` for available commands

**Options:**

- Add ``--read-only`` to prevent writes to your B-Fabric instance during testing
- Add ``--use-external-runner`` if ``bfabric-app-runner`` is available externally (otherwise requires ``uv``)

The generated Makefile uses ``bfabric-app-runner action`` commands internally.
"""

from __future__ import annotations

import importlib.metadata

import cyclopts

from bfabric_app_runner.cli.cmd_action import (
    cmd_action_inputs,
    cmd_action_outputs,
    cmd_action_process,
    cmd_action_run_all,
    cmd_action_dispatch,
)
from bfabric_app_runner.cli.cmd_prepare import cmd_prepare_workunit
from bfabric_app_runner.cli.cmd_run import cmd_run_workunit
from bfabric_app_runner.cli.inputs import cmd_inputs_prepare, cmd_inputs_clean, cmd_inputs_list, cmd_inputs_check
from bfabric_app_runner.cli.outputs import cmd_outputs_register, cmd_outputs_register_single_file
from bfabric_app_runner.cli.validate import (
    cmd_validate_inputs_spec,
    cmd_validate_outputs_spec,
    cmd_validate_app_spec,
    cmd_validate_app_spec_template,
)


package_version = importlib.metadata.version("bfabric_app_runner")
app = cyclopts.App(
    help=__doc__,
    version=package_version,
)

groups = {
    "Running Apps": cyclopts.Group("Running Apps", sort_key=1),
    "Developer Tools": cyclopts.Group("Developer Tools", sort_key=2),
}


cmd_inputs = cyclopts.App("inputs", help="Prepare input files for an app.")
cmd_inputs.command(cmd_inputs_check, name="check")
cmd_inputs.command(cmd_inputs_clean, name="clean")
cmd_inputs.command(cmd_inputs_list, name="list")
cmd_inputs.command(cmd_inputs_prepare, name="prepare")
cmd_inputs.group = groups["Developer Tools"]
app.command(cmd_inputs)

cmd_outputs = cyclopts.App("outputs", help="Register output files of an app.")
cmd_outputs.command(cmd_outputs_register, name="register")
cmd_outputs.command(cmd_outputs_register_single_file, name="register-single-file")
cmd_outputs.group = groups["Developer Tools"]
app.command(cmd_outputs)

cmd_validate = cyclopts.App("validate", help="Validate yaml files.")
cmd_validate.command(cmd_validate_app_spec, name="app-spec")
cmd_validate.command(cmd_validate_app_spec_template, name="app-spec-template")
cmd_validate.command(cmd_validate_inputs_spec, name="inputs-spec")
cmd_validate.command(cmd_validate_outputs_spec, name="outputs-spec")
cmd_validate.group = groups["Developer Tools"]
app.command(cmd_validate)

cmd_action = cyclopts.App("action", help="Executes an action of a prepared workunit")
cmd_action.command(cmd_action_run_all, name="run-all")
cmd_action.command(cmd_action_dispatch, name="dispatch")
cmd_action.command(cmd_action_inputs, name="inputs")
cmd_action.command(cmd_action_process, name="process")
cmd_action.command(cmd_action_outputs, name="outputs")
cmd_action.group = groups["Developer Tools"]
app.command(cmd_action)

cmd_prepare = cyclopts.App(name="prepare", help="Prepare a workunit for execution.")
cmd_prepare.command(cmd_prepare_workunit, name="workunit")
cmd_prepare.group = groups["Running Apps"]
app.command(cmd_prepare)

cmd_run = cyclopts.App(name="run", help="Run an app end-to-end.")
cmd_run.command(cmd_run_workunit, name="workunit")
cmd_run.group = groups["Running Apps"]
app.command(cmd_run)

if __name__ == "__main__":
    app()
