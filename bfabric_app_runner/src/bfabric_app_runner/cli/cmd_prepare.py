import copy
from pathlib import Path

import yaml

from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition, WorkunitExecutionDefinition
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.actions.config_file import ActionConfig
from bfabric_app_runner.prepare.local_workunit_definition import LocalWorkunitExecutionDefinition
from bfabric_app_runner.prepare.makefile_template import render_makefile
from bfabric_app_runner.specs.app.app_spec import AppSpec


def _update_app_version[T: (
    WorkunitExecutionDefinition,
    LocalWorkunitExecutionDefinition,
)](workunit_execution_definition: T, application_version: str) -> T:
    # TODO if this is useful consider moving it to the WorkunitDefinition class
    workunit_execution_definition = copy.deepcopy(workunit_execution_definition)
    workunit_execution_definition.raw_parameters["application_version"] = application_version
    return workunit_execution_definition


@use_client
def cmd_prepare_workunit(
    app_spec: Path,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    force_app_version: str | None = None,
    read_only: bool = False,
    use_external_runner: bool = False,
    client: Bfabric,
) -> None:
    """Prepares a workunit for processing.

    :param app_spec: The path to the application specification.
    :param work_dir: The directory where the workunit execution will be executed later.
    :param workunit_ref: The reference to the workunit, can be an ID or a path to a YAML file.
    :param ssh_user: The SSH user to use for file operations (if not provided, defaults to the current user).
    :param force_storage: (for testing) storage definition to use for the workunit output instead of the configured one.
    :param force_app_version: (for testing) specific application version instead of the workunit's `application_version`
    :param read_only: If True, no results will be written to B-Fabric.
    :param use_external_runner: If True, allows using external bfabric-app-runner from PATH instead of exact version.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client=client)
    if force_app_version:
        workunit_definition.execution = _update_app_version(
            workunit_execution_definition=workunit_definition.execution, application_version=force_app_version
        )

    # Resolve the app version early, following the pattern used by other commands
    app_full_spec = AppSpec.load_yaml(
        app_yaml=app_spec,
        app_id=workunit_definition.registration.application_id,
        app_name=workunit_definition.registration.application_name,
    )

    workunit_definition_path = work_dir / "workunit_definition.yml"
    workunit_definition.to_yaml(path=workunit_definition_path)
    _write_app_env_file(
        path=work_dir / "app_env.yml",
        app_ref=app_spec.resolve(),
        workunit_ref=workunit_definition_path,
        ssh_user=ssh_user,
        force_storage=force_storage,
        read_only=read_only,
    )
    # Render the workunit Makefile template
    render_makefile(
        path=work_dir / "Makefile",
        bfabric_app_spec=app_full_spec.bfabric,
        rename_existing=True,
        use_external_runner=use_external_runner,
    )


def cmd_prepare_local_workunit(
    app_spec: Path,
    work_dir: Path,
    workunit_ref: Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    force_app_version: str | None = None,
    read_only: bool = False,
    use_external_runner: bool = False,
    # TODO these two are a bit weird but required right now (because they correspond to registration and not execution)
    app_id: int = 0,
    app_name: str = "local_app",
) -> None:
    """Exprimental: Prepares a local workunit for processing."""
    # TODO this is mostly cmd_prepare_workunit with some changes
    work_dir.mkdir(parents=True, exist_ok=True)
    workunit_execution_definition = LocalWorkunitExecutionDefinition.from_yaml(workunit_ref)
    if force_app_version:
        workunit_execution_definition = _update_app_version(
            workunit_execution_definition=workunit_execution_definition, application_version=force_app_version
        )

    # Resolve the app version early, following the pattern used by other commands
    app_full_spec = AppSpec.load_yaml(app_yaml=app_spec, app_id=app_id, app_name=app_name)

    workunit_definition_path = work_dir / "workunit_definition.yml"
    workunit_execution_definition.to_yaml(path=workunit_definition_path)
    _write_app_env_file(
        path=work_dir / "app_env.yml",
        app_ref=app_spec.resolve(),
        workunit_ref=workunit_definition_path,
        ssh_user=ssh_user,
        force_storage=force_storage,
        read_only=read_only,
    )
    # Render the workunit Makefile template
    render_makefile(
        path=work_dir / "Makefile",
        bfabric_app_spec=app_full_spec.bfabric,
        rename_existing=True,
        use_external_runner=use_external_runner,
    )


def _write_app_env_file(
    path: Path,
    app_ref: Path,
    workunit_ref: Path,
    ssh_user: str | None,
    force_storage: Path | None,
    read_only: bool,
) -> None:
    # TODO this handles everything except the BFABRIPY_CONFIG_OVERRIDE

    action_config = ActionConfig(
        work_dir=path.parent.resolve(),
        app_ref=app_ref,
        workunit_ref=workunit_ref,
        ssh_user=ssh_user,
        force_storage=force_storage,
        read_only=read_only,
    )

    data = {"bfabric_app_runner": {"action": action_config.model_dump(mode="json")}}
    with path.open("w") as fh:
        yaml.safe_dump(data, fh)
