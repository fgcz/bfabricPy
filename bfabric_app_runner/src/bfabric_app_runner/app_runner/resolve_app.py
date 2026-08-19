from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_app_runner.specs.app.app_spec import AppSpec, BfabricAppSpec

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric import Bfabric
    from bfabric_app_runner.specs.app.app_version import AppVersion


def _resolve_app(versions: AppSpec, workunit_definition: WorkunitDefinition) -> AppVersion:
    """Resolves the app version to use for the provided workunit definition."""
    app_version = versions.for_parameters(workunit_definition.execution.raw_parameters)
    if app_version is None:
        requested = workunit_definition.execution.raw_parameters.get("application_version")
        reason = (
            "the workunit definition does not specify an application_version"
            if requested is None
            else f"application_version '{requested}' is not defined in the app spec"
        )
        msg = f"Cannot resolve the app version: {reason},\n available versions: {sorted(versions.available_versions)}"
        raise ValueError(msg)
    return app_version


def load_workunit_information(
    app_spec: Path, client: Bfabric, work_dir: Path, workunit_ref: int | Path
) -> tuple[AppVersion, BfabricAppSpec, Path]:
    """Loads the app version and workunit definition from the provided app spec and workunit reference.

    :param app_spec: Path to the app spec file.
    :param client: The B-Fabric client to use for resolving the workunit.
    :param work_dir: Path to the work directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :return app_version: The app version to use.
    :return bfabric_app_spec: The B-Fabric app spec, which specifies the app runner version to use.
    :return workunit_ref: The path to the workunit definition file. If the workunit_ref was already a path, it will be
        returned as is, otherwise the file will be created in the work directory.
    """
    workunit_definition, workunit_ref = _resolve_workunit_definition(client, work_dir, workunit_ref)
    app_spec = AppSpec.load_yaml(
        app_spec,
        app_id=workunit_definition.registration.application_id,
        app_name=workunit_definition.registration.application_name,
    )
    app_version = _resolve_app(versions=app_spec, workunit_definition=workunit_definition)
    bfabric_app_spec = app_spec.bfabric
    return app_version, bfabric_app_spec, workunit_ref


def _resolve_workunit_definition(
    client: Bfabric, work_dir: Path, workunit_ref: int | Path
) -> tuple[WorkunitDefinition, Path]:
    """Load the specified workunit definition.

    If the workunit_definition.yml file exists in the work_dir, it will be used, otherwise, it will be created.
    :param client: The B-Fabric client to use for resolving the workunit.
    :param work_dir: The directory where the workunit definition file will be created or found.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :return: A tuple containing the WorkunitDefinition and the path to the workunit definition file.
    """
    workunit_definition_file = work_dir / "workunit_definition.yml"
    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client, cache_file=workunit_definition_file)
    return workunit_definition, workunit_definition_file
