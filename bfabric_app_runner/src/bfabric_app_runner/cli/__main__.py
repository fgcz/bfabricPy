from __future__ import annotations

import importlib.metadata

import cyclopts

from bfabric_app_runner.cli.app import cmd_app_run, cmd_app_dispatch
from bfabric_app_runner.cli.chunk import cmd_chunk_run_all, cmd_chunk_outputs, cmd_chunk_process
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
    help="Provides an entrypoint to app execution.\n\nFunctionality/API under active development!",
    version=package_version,
)

cmd_app = cyclopts.App("app", help="Run an app.")
cmd_app.command(cmd_app_dispatch, name="dispatch")
cmd_app.command(cmd_app_run, name="run")
app.command(cmd_app)

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

app.command(cmd_validate)

if __name__ == "__main__":
    app()
