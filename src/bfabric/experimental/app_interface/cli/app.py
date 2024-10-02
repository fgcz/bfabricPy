from __future__ import annotations

from pathlib import Path

import cyclopts
import yaml

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.app_interface.app_runner._spec import AppSpec
from bfabric.experimental.app_interface.app_runner.runner import run_app, Runner

app_app = cyclopts.App("app", help="Run an app.")


@app_app.command()
def run(
    app_spec: Path,
    target_folder: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    read_only: bool = False,
) -> None:
    """Runs all stages of an app."""
    # TODO doc
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
    work_dir: Path,
    workunit_ref: int | Path,
) -> None:
    """Create chunks, which can be processed individually.

    :param app_spec: Path to the app spec file.
    :param work_dir: Path to the work directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    """
    setup_script_logging()
    # TODO set workunit to processing? (i.e. add read-only option here)
    client = Bfabric.from_config()
    runner = Runner(spec=AppSpec.model_validate(yaml.safe_load(app_spec.read_text())), client=client, ssh_user=None)
    runner.run_dispatch(workunit_ref=workunit_ref, work_dir=work_dir)
