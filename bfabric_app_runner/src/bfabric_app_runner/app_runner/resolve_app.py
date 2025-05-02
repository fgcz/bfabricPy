from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import ValidationError

from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_app_runner.specs.app.app_spec import AppSpec
from bfabric_app_runner.specs.app.app_version import AppVersion

if TYPE_CHECKING:
    from bfabric import Bfabric


def _resolve_app(versions: AppSpec, workunit_definition: WorkunitDefinition) -> AppVersion:
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
    app_spec: Path | str, client: Bfabric, work_dir: Path, workunit_ref: int | Path
) -> tuple[AppVersion, Path]:
    """Loads the app version and workunit definition from the provided app spec and workunit reference.

    Syntax for app_spec when it is a string is either:
    - `my.package` which implies the `app.yml` is available at `my/package/integrations/bfabric/app.yml`
    - `my.package.integrations.bfabric:app.yml` which implies the `app.yml` is available at the same location as before

    :param app_spec: Path to the app spec Python module or file.
    :param client: The B-Fabric client to use for resolving the workunit.
    :param work_dir: Path to the work directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :return app_version: The app version to use.
    :return workunit_ref: Path to the workunit definition file. Can be used to reference the workunit in further
        steps to avoid unnecessary B-Fabric lookups. (If the workunit_ref was already a path, it will be returned as is,
        otherwise the file will be created in the work directory.)
    """
    workunit_definition, workunit_ref = _resolve_workunit_definition(client, work_dir, workunit_ref)
    app_version = _resolve_app_version(app_spec, workunit_definition)
    return app_version, workunit_ref


def _resolve_app_version(app_spec: Path | str, workunit_definition: WorkunitDefinition) -> AppVersion:
    if isinstance(app_spec, Path) and app_spec.exists():
        app_parsed = _load_spec(
            app_spec, workunit_definition.registration.application_id, workunit_definition.registration.application_name
        )
    else:
        if ":" in app_spec:
            yaml_module, yaml_file = app_spec.split(":")
        else:
            yaml_module = f"{app_spec}.integrations.bfabric"
            yaml_file = "app.yml"
        app_parsed = AppVersion.model_validate(yaml.safe_load(importlib.resources.read_text(yaml_module, yaml_file)))
        # TODO app version makes less sense in this case and we would want to have some sort of interpolation
    if isinstance(app_parsed, AppVersion):
        app_version = app_parsed
    else:
        app_version = _resolve_app(versions=app_parsed, workunit_definition=workunit_definition)
    return app_version


def _resolve_workunit_definition(
    client: Bfabric, work_dir: Path, workunit_ref: int | Path
) -> tuple[WorkunitDefinition, Path]:
    """Given a workunit reference (ID or YAML file path), loads the workunit definition and returns it.

    You get both the workunit definition and the path to the workunit definition file, which will be created if it
    did not exist before in `work_dir`.
    """
    workunit_definition_file = work_dir / "workunit_definition.yml"
    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client, cache_file=workunit_definition_file)
    return workunit_definition, workunit_definition_file
