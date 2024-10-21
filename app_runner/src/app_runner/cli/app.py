from __future__ import annotations

from pathlib import Path

import cyclopts
import yaml

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from app_runner.app_runner._spec import AppSpec
from app_runner.app_runner.runner import run_app, Runner
from bfabric.experimental.entity_lookup_cache import EntityLookupCache

app_app = cyclopts.App("app", help="Run an app.")


@app_app.command()
def run(
    app_spec: Path,
    work_dir: Path,
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
    with EntityLookupCache.enable():
        run_app(
            app_spec=app_spec_parsed,
            workunit_ref=workunit_ref,
            work_dir=work_dir,
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
    work_dir = work_dir.resolve()
    # TODO set workunit to processing? (i.e. add read-only option here)
    client = Bfabric.from_config()
    with EntityLookupCache.enable():
        runner = Runner(spec=AppSpec.model_validate(yaml.safe_load(app_spec.read_text())), client=client, ssh_user=None)
        runner.run_dispatch(workunit_ref=workunit_ref, work_dir=work_dir)
