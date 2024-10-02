from __future__ import annotations

from pathlib import Path

import cyclopts
import yaml

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.entities import Workunit
from bfabric.experimental.app_interface.app_runner._spec import AppSpec
from bfabric.experimental.app_interface.app_runner.runner import run_app, Runner
from bfabric.experimental.app_interface.input_preparation import prepare_folder
from bfabric.experimental.app_interface.input_preparation.prepare import print_input_files_list
from bfabric.experimental.app_interface.output_registration._spec import OutputsSpec
from bfabric.experimental.app_interface.output_registration.register import register_all

app = cyclopts.App()
app_inputs = cyclopts.App("inputs", help="Prepare input files for an app.")
app.command(app_inputs)
app_outputs = cyclopts.App("outputs", help="Register output files for an app.")
app.command(app_outputs)
app_app = cyclopts.App("app", help="Run an app.")
app.command(app_app)
app_chunk = cyclopts.App("chunk", help="Run an app on a chunk. You can create the chunks with `app dispatch`.")
app.command(app_chunk)


@app_inputs.command()
def prepare(
    inputs_yaml: Path,
    target_folder: Path | None = None,
    *,
    ssh_user: str | None = None,
) -> None:
    """Prepare the input files by downloading them (if necessary).

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be downloaded.
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        ssh_user=ssh_user,
        client=client,
        action="prepare",
    )


@app_inputs.command()
def clean(
    inputs_yaml: Path,
    target_folder: Path | None = None,
) -> None:
    """Removes all local copies of input files.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be removed.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    # TODO clean shouldn't even need all these arguments, this could be refactored later
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        ssh_user=None,
        action="clean",
        client=client,
    )


@app_inputs.command()
def list(
    inputs_yaml: Path,
    target_folder: Path | None = None,
) -> None:
    """Lists the input files for an app."""
    setup_script_logging()
    print_input_files_list(inputs_yaml=inputs_yaml, target_folder=target_folder)


@app_outputs.command()
def register(
    outputs_yaml: Path,
    # TODO we should use the workunit definition instead
    workunit_id: int,
    *,
    ssh_user: str | None = None,
    # TODO
    reuse_default_resource: bool = True,
) -> None:
    """Register the output files of a workunit."""
    setup_script_logging()
    client = Bfabric.from_config()

    specs_list = OutputsSpec.read_yaml(outputs_yaml)
    workunit = Workunit.find(id=workunit_id, client=client)
    register_all(
        client=client,
        workunit=workunit,
        specs_list=specs_list,
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )


@app_app.command()
def run(
    app_spec: Path,
    workunit_ref: int | Path,
    target_folder: Path,
    *,
    ssh_user: str | None = None,
    read_only: bool = False,
) -> None:
    """Runs all stages of an app."""
    setup_script_logging()
    client = Bfabric.from_config()
    app_spec_parsed = AppSpec.model_validate(yaml.safe_load(app_spec.read_text()))
    run_app(
        app_spec=app_spec_parsed,
        workunit_ref=workunit_ref,
        work_dir=target_folder,
        client=client,
        ssh_user=ssh_user,
        read_only=read_only,
    )


@app_app.command()
def dispatch(
    app_spec: Path,
    workunit_ref: int | Path,
    work_dir: Path,
) -> None:
    """Create chunks, which can be processed individually.

    :param app_spec: Path to the app spec file.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :param work_dir: Path to the work directory.
    """
    setup_script_logging()
    # TODO set workunit to processing? (i.e. add read-only option here)
    client = Bfabric.from_config()
    runner = Runner(spec=AppSpec.model_validate(yaml.safe_load(app_spec.read_text())), client=client, ssh_user=None)
    runner.run_dispatch(workunit_ref=workunit_ref, work_dir=work_dir)


@app_chunk.command()
def run_all(
    app_spec: Path,
    workunit_ref: int | Path,
    work_dir: Path,
    *,
    ssh_user: str | None = None,
    read_only: bool = False,
) -> None:
    """Run all chunks, including input preparation, processing, and output registration.

    :param app_spec: Path to the app spec file.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :param work_dir: Path to the work directory.
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    :param read_only: If True, results will not be registered and the workunit status will not be changed.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    app_spec_parsed = AppSpec.model_validate(yaml.safe_load(app_spec.read_text()))

    run_app(
        app_spec=app_spec_parsed,
        workunit_ref=workunit_ref,
        work_dir=work_dir,
        client=client,
        ssh_user=ssh_user,
        read_only=read_only,
        dispatch_active=False,
    )


@app_chunk.command()
def inputs(
    chunk_dir: Path,
    *,
    ssh_user: str | None = None,
) -> None:
    """Prepare the input files for a chunk.

    :param chunk_dir: Path to the chunk directory.
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    runner = Runner(spec=AppSpec(), client=client, ssh_user=ssh_user)
    runner.run_prepare_input(chunk_dir=chunk_dir)


@app_chunk.command()
def process(chunk_dir: Path) -> None:
    """Process a chunk.

    Note that the input files must be prepared before running this command.
    :param chunk_dir: Path to the chunk directory.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    runner = Runner(spec=AppSpec(), client=client, ssh_user=None)
    runner.run_process(chunk_dir=chunk_dir)


@app_chunk.command()
def outputs(
    chunk_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    read_only: bool = False,
    reuse_default_resource: bool = True,
) -> None:
    """Register the output files of a chunk.

    :param chunk_dir: Path to the chunk directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    :param read_only: If True, the workunit will not be set to processing.
    :param reuse_default_resource: If True, the default resource will be reused for the output files. (recommended)
    """
    setup_script_logging()
    client = Bfabric.from_config()
    runner = Runner(spec=AppSpec(), client=client, ssh_user=ssh_user)
    runner.run_collect(workunit_ref=workunit_ref, chunk_dir=chunk_dir)
    if not read_only:
        runner.run_register_outputs(
            chunk_dir=chunk_dir, workunit_ref=workunit_ref, reuse_default_resource=reuse_default_resource
        )


if __name__ == "__main__":
    app()
