from __future__ import annotations

from pathlib import Path

import cyclopts
import yaml

from app_runner.specs.app.app_spec import AppVersion
from app_runner.app_runner.runner import run_app, Runner
from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.entity_lookup_cache import EntityLookupCache

app_chunk = cyclopts.App("chunk", help="Run an app on a chunk. You can create the chunks with `app dispatch`.")


@app_chunk.command()
def run_all(
    app_spec: Path,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    read_only: bool = False,
) -> None:
    """Run all chunks, including input preparation, processing, and output registration.

    :param app_spec: Path to the app spec file.
    :param work_dir: Path to the work directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    :param read_only: If True, results will not be registered and the workunit status will not be changed.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    app_spec_parsed = AppVersion.model_validate(yaml.safe_load(app_spec.read_text()))

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
def process(app_spec: Path, chunk_dir: Path) -> None:
    """Process a chunk.

    Note that the input files must be prepared before running this command.
    :param app_spec: Path to the app spec file.
    :param chunk_dir: Path to the chunk directory.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    chunk_dir = chunk_dir.resolve()
    app_spec_parsed = AppVersion.model_validate(yaml.safe_load(app_spec.read_text()))

    with EntityLookupCache.enable():
        # TODO NEEDS FIX
        runner = Runner(spec=app_spec_parsed, client=client, ssh_user=None)
        runner.run_process(chunk_dir=chunk_dir)


@app_chunk.command()
def outputs(
    app_spec: Path,
    chunk_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    read_only: bool = False,
    reuse_default_resource: bool = True,
) -> None:
    """Register the output files of a chunk.

    :param app_spec: Path to the app spec file.
    :param chunk_dir: Path to the chunk directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    :param read_only: If True, the workunit will not be set to processing.
    :param reuse_default_resource: If True, the default resource will be reused for the output files. (recommended)
    """
    setup_script_logging()
    client = Bfabric.from_config()
    chunk_dir = chunk_dir.resolve()
    app_spec_parsed = AppVersion.model_validate(yaml.safe_load(app_spec.read_text()))

    # TODO NEEDS FIX
    runner = Runner(spec=app_spec_parsed, client=client, ssh_user=ssh_user)
    runner.run_collect(workunit_ref=workunit_ref, chunk_dir=chunk_dir)
    if not read_only:
        runner.run_register_outputs(
            chunk_dir=chunk_dir, workunit_ref=workunit_ref, reuse_default_resource=reuse_default_resource
        )
