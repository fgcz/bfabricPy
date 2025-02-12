from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import ValidationError

from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_app_runner.specs.app.app_spec import AppSpec
from bfabric_app_runner.specs.app.app_version import AppVersion

if TYPE_CHECKING:
    from bfabric import Bfabric


def resolve_app(versions: AppSpec, workunit_definition: WorkunitDefinition) -> AppVersion:
    """Resolves the app version to use for the provided workunit definition."""
    # TODO this should be more generic in the future about the key for the app version (should be handled in AppSpec)
    # TODO logic to define "latest" version (should also be handled in AppSpec)
    if "application_version" not in workunit_definition.execution.raw_parameters:
        raise ValueError("The workunit definition does not contain an application version.")
    app_version = workunit_definition.execution.raw_parameters["application_version"]
    # TODO graceful handling of invalid versions
    if app_version in versions and versions[app_version] is not None:
        return versions[app_version]
    else:
        msg = (
            f"application_version '{app_version}' is not defined in the app spec,\n"
            f" available versions: {sorted(versions.available_versions)}"
        )
        raise ValueError(msg)
    return versions[app_version]


def _load_spec(spec_path: Path, app_id: int, app_name: str) -> AppVersion | AppSpec:
    # TODO the reason this exists is I don't want to refactor and complicate the CLI right now, however,
    #      it is not fully clear if this is perfectly sound in all cases.
    data = yaml.safe_load(spec_path.read_text())
    try:
        return AppVersion.model_validate(data)
    except ValidationError:
        return AppSpec.load_yaml(spec_path, app_id=app_id, app_name=app_name)


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
    if isinstance(workunit_ref, Path):
        workunit_ref = workunit_ref.resolve()
    workunit_definition_file = work_dir / "workunit_definition.yml"
    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client, cache_file=workunit_definition_file)
    app_parsed = _load_spec(
        app_spec, workunit_definition.registration.application_id, workunit_definition.registration.application_name
    )

    if isinstance(workunit_ref, int):
        workunit_ref = workunit_definition_file
    if isinstance(app_parsed, AppVersion):
        app_version = app_parsed
    else:
        app_version = resolve_app(versions=app_parsed, workunit_definition=workunit_definition)
    return app_version, workunit_ref
