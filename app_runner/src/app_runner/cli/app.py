from __future__ import annotations

from pathlib import Path

import cyclopts

from app_runner.app_runner.resolve_app import resolve_app
from app_runner.app_runner.runner import run_app, Runner
from app_runner.specs.app.app_spec import AppVersion
from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.entity_lookup_cache import EntityLookupCache
from bfabric.experimental.workunit_definition import WorkunitDefinition

app_app = cyclopts.App("app", help="Run an app.")


def load_workunit_information(
    app_spec: Path, client: Bfabric, work_dir: Path, workunit_ref: int | Path
) -> tuple[AppVersion, Path]:
    """Loads the app version and workunit definition from the provided app spec and workunit reference.

    :param app_spec: Path to the app spec file.
    :param client: The B-Fabric client to use for resolving the workunit.
    :param work_dir: Path to the work directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :return app_version: The app version to use.
    :return workunit_ref: Path to the workunit definition file. Can be used to reference the workunit in further
        steps to avoid unnecessary B-Fabric lookups. (If the workunit_ref was already a path, it will be returned as is,
        otherwise the file will be created in the work directory.)
    """
    # TODO and migrate since it will be useful for other commands as well
    app_versions = AppVersion.load_yaml(app_spec)
    workunit_definition_file = work_dir / "workunit_definition.yml"
    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client, cache_file=workunit_definition_file)
    if isinstance(workunit_ref, int):
        workunit_ref = workunit_definition_file
    app_version = resolve_app(versions=app_versions, workunit_definition=workunit_definition)
    return app_version, workunit_ref


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
