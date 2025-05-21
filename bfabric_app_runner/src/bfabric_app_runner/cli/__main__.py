from __future__ import annotations

import importlib.metadata

import cyclopts

from bfabric_app_runner.cli.app import cmd_app_run, cmd_app_dispatch
from bfabric_app_runner.cli.chunk import cmd_chunk_run_all, cmd_chunk_outputs, cmd_chunk_process
from bfabric_app_runner.cli.cmd_action import (
    cmd_action_inputs,
    cmd_action_outputs,
    cmd_action_process,
    cmd_action_run_all,
    cmd_action_dispatch,
)
from bfabric_app_runner.cli.cmd_deploy import cmd_deploy_build_app_zip
from bfabric_app_runner.cli.cmd_prepare import cmd_prepare_workunit
from bfabric_app_runner.cli.inputs import cmd_inputs_prepare, cmd_inputs_clean, cmd_inputs_list, cmd_inputs_check
from bfabric_app_runner.cli.outputs import cmd_outputs_register, cmd_outputs_register_single_file
from bfabric_app_runner.cli.validate import (
    cmd_validate_inputs_spec,
    cmd_validate_outputs_spec,
    cmd_validate_app_spec,
    cmd_validate_app_spec_template,
    cmd_validate_submitters_spec_template,
)

package_version = importlib.metadata.version("bfabric_app_runner")
app = cyclopts.App(
    help="Provides an entrypoint to app execution.\n\nFunctionality/API under active development!",
    version=package_version,
)

cmd_app = cyclopts.App(help="Run an app.")
cmd_app.command(cmd_app_dispatch, name="dispatch")
cmd_app.command(cmd_app_run, name="run")
app.command(cmd_app, name="app")

cmd_inputs = cyclopts.App("inputs", help="Prepare input files for an app.")
cmd_inputs.command(cmd_inputs_check, name="check")
cmd_inputs.command(cmd_inputs_clean, name="clean")
cmd_inputs.command(cmd_inputs_list, name="list")
cmd_inputs.command(cmd_inputs_prepare, name="prepare")
app.command(cmd_inputs)

cmd_outputs = cyclopts.App("outputs", help="Register output files of an app.")
cmd_outputs.command(cmd_outputs_register, name="register")
cmd_outputs.command(cmd_outputs_register_single_file, name="register-single-file")
app.command(cmd_outputs)

cmd_chunk = cyclopts.App("chunk", help="Run an app on a chunk. You can create the chunks with `app dispatch`.")
cmd_chunk.command(cmd_chunk_outputs, name="outputs")
cmd_chunk.command(cmd_chunk_process, name="process")
cmd_chunk.command(cmd_chunk_run_all, name="run-all")
app.command(cmd_chunk)

cmd_validate = cyclopts.App("validate", help="Validate yaml files.")
cmd_validate.command(cmd_validate_app_spec, name="app-spec")
cmd_validate.command(cmd_validate_app_spec_template, name="app-spec-template")
cmd_validate.command(cmd_validate_inputs_spec, name="inputs-spec")
cmd_validate.command(cmd_validate_outputs_spec, name="outputs-spec")
cmd_validate.command(cmd_validate_submitters_spec_template, name="submitters-spec-template")
app.command(cmd_validate)

cmd_action = cyclopts.App("action", help="Executes an action of a prepared workunit")
cmd_action.command(cmd_action_run_all, name="run-all")
cmd_action.command(cmd_action_dispatch, name="dispatch")
cmd_action.command(cmd_action_inputs, name="inputs")
cmd_action.command(cmd_action_process, name="process")
cmd_action.command(cmd_action_outputs, name="outputs")
app.command(cmd_action)

cmd_prepare = cyclopts.App(name="prepare")
cmd_prepare.command(cmd_prepare_workunit, name="workunit")
app.command(cmd_prepare)

cmd_deploy = cyclopts.App(name="deploy", help="Utilities for deploying apps")
cmd_deploy.command(cmd_deploy_build_app_zip, name="build-app-zip")
app.command(cmd_deploy)


if __name__ == "__main__":
    app()
