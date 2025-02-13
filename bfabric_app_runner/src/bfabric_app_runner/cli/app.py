from __future__ import annotations

import importlib.metadata
import importlib.resources
from pathlib import Path

import cyclopts
from loguru import logger

from bfabric import Bfabric
from bfabric.experimental.entity_lookup_cache import EntityLookupCache
from bfabric.utils.cli_integration import setup_script_logging
from bfabric_app_runner.app_runner.resolve_app import load_workunit_information
from bfabric_app_runner.app_runner.runner import run_app, Runner

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
    app_version, workunit_ref = load_workunit_information(app_spec, client, work_dir, workunit_ref)

    copy_dev_makefile(work_dir=work_dir)

    # TODO(#107): usage of entity lookup cache was problematic -> beyond the full solution we could also consider
    #             to deactivate the cache for the output registration
    # with EntityLookupCache.enable():
    run_app(
        app_spec=app_version,
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

    app_version, workunit_ref = load_workunit_information(app_spec, client, work_dir, workunit_ref)

    with EntityLookupCache.enable():
        runner = Runner(spec=app_version, client=client, ssh_user=None)
        runner.run_dispatch(workunit_ref=workunit_ref, work_dir=work_dir)


def copy_dev_makefile(work_dir: Path) -> None:
    """Copies the workunit.mk file to the work directory, and sets the version of the app runner."""
    with importlib.resources.path("bfabric_app_runner", "resources/workunit.mk") as source_path:
        target_path = work_dir / "Makefile"

        makefile_template = target_path.read_text()
        app_runner_version = importlib.metadata.version("bfabric_app_runner")
        makefile = makefile_template.replace("@RUNNER_VERSION@", app_runner_version)

        if target_path.exists():
            logger.info("Renaming existing Makefile to Makefile.bak")
            target_path.rename(work_dir / "Makefile.bak")
        logger.info(f"Copying Makefile from {source_path} to {target_path}")
        target_path.parent.mkdir(exist_ok=True, parents=True)
        target_path.write_text(makefile)
