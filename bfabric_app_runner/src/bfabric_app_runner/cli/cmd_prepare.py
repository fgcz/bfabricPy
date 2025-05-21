import importlib.resources
import os
from pathlib import Path

import yaml
from loguru import logger

from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.actions.config_file import ActionConfig


@use_client
def cmd_prepare_workunit(
    app_spec: Path | str,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    read_only: bool = False,
    client: Bfabric,
) -> None:
    """Prepares a workunit for processing."""
    work_dir.mkdir(parents=True, exist_ok=True)

    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client=client)
    workunit_definition_path = work_dir / "workunit_definition.yml"
    workunit_definition.to_yaml(path=workunit_definition_path)
    _write_app_env_file(
        path=work_dir / "app_env.yml",
        # TODO previously we sometimes copied it but now it will not always be supported (could be added later)
        app_ref=app_spec,
        workunit_ref=workunit_definition_path,
        ssh_user=ssh_user,
        force_storage=force_storage,
        read_only=read_only,
    )
    _write_workunit_makefile(path=work_dir / "Makefile")


def _write_workunit_makefile(path: Path) -> None:
    makefile = importlib.resources.read_text("bfabric_app_runner", "resources/workunit.mk")

    # TODO this should be improved (using env variable isn't reliable)
    app_runner_cmd = os.environ.get("APP_RUNNER_COMMAND") or "bfabric-app-runner"
    # For makefile escaping of URIs containing `#` character
    app_runner_cmd = app_runner_cmd.replace(r"#", r"\#")
    makefile = makefile.replace("@APP_RUNNER_CMD@", app_runner_cmd)

    if path.exists():
        logger.info("Renaming existing Makefile to Makefile.bak")
        path.rename(path.parent / "Makefile.bak")
    logger.info(f"Writing rendered Makefile to {path}")
    path.write_text(makefile)


def _write_app_env_file(
    path: Path,
    app_ref: Path | str,
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
