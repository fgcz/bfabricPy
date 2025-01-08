from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.experimental.workunit_definition import WorkunitDefinition

from app_runner.specs.app.app_spec import AppVersions

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric import Bfabric
    from app_runner.specs.app.app_version import AppVersion


def resolve_app(versions: AppVersions, workunit_definition: WorkunitDefinition) -> AppVersion:
    """Resolves the app version to use for the provided workunit definition."""
    # TODO this should be more generic in the future
    # TODO logic to define "latest" version
    app_version = workunit_definition.execution.raw_parameters["application_version"]
    # TODO graceful handling of invalid versions
    return versions[app_version]


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
    workunit_definition_file = work_dir / "workunit_definition.yml"
    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client, cache_file=workunit_definition_file)
    app_versions = AppVersions.load_yaml(
        app_spec,
        app_id=workunit_definition.registration.application_id,
        app_name=workunit_definition.registration.application_name,
    )
    if isinstance(workunit_ref, int):
        workunit_ref = workunit_definition_file
    app_version = resolve_app(versions=app_versions, workunit_definition=workunit_definition)
    return app_version, workunit_ref
