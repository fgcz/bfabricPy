import importlib.metadata
import importlib.resources
import os
import shlex
import sys
from pathlib import Path

from loguru import logger

from bfabric.config.config_data import ConfigData, export_config_data


def _get_runner_cmd(wheel_path: str | None = None) -> str:
    if wheel_path is None:
        app_runner_version = importlib.metadata.version("bfabric_app_runner")
        cmd = ["uv", "run", "-p", "3.13", "--with", f"bfabric-app-runner=={app_runner_version}", "bfabric-app-runner"]
    else:
        # TODO chicken-egg problem -> where do you get this info from?
        cmd = ["uv", "run", "-p", "3.13", "--with", wheel_path, "--refresh", "bfabric-app-runner"]
    return shlex.join(cmd)


def _render_makefile(app_def: Path | str) -> str:
    template_variables = {
        "RUNNER_CMD": _get_runner_cmd(),
        "APP_DEF": str(app_def),
    }

    with importlib.resources.path("bfabric_app_runner", "resources/workunit.mk") as source_path:
        logger.info(f"Rendering Makefile template from {source_path} with variables: {template_variables!r}")
        makefile = source_path.read_text()
        for key, value in template_variables.items():
            makefile = makefile.replace(f"@{key}@", value)
        return makefile


def _render_env_file(config_data: ConfigData) -> str:
    json_string = export_config_data(config_data)
    env_file_content = f'BFABRICPY_CONFIG_OVERRIDE="{json_string.replace('"', '\\"')}"\n'
    return env_file_content


def copy_dev_makefile(
    work_dir: Path, app_definition: Path | str, config_data: ConfigData, create_env_file: bool
) -> None:
    """Copies the workunit.mk file to the work directory, and sets the version of the app runner.

    It also creates a .env file containing the BFABRICPY_CONFIG_OVERRIDE environment variable containing the configured
    connection. For security reasons it will be chmod 600.
    """
    makefile = _render_makefile(app_def=app_definition)
    target_path = work_dir / "Makefile"
    if target_path.exists():
        logger.info("Renaming existing Makefile to Makefile.bak")
        target_path.rename(work_dir / "Makefile.bak")
    logger.info(f"Writing rendered Makefile to {target_path}")
    target_path.parent.mkdir(exist_ok=True, parents=True)
    target_path.write_text(makefile)

    if create_env_file:
        env_file_content = _render_env_file(config_data)
        env_file_path = work_dir / ".env"
        if env_file_path.exists():
            logger.info("Renaming existing .env file to .env.bak")
            env_file_path.rename(work_dir / ".env.bak")
        logger.info(f"Creating .env file at {env_file_path}")
        _write_file_chmod(path=env_file_path, text=env_file_content, mode=0o600)


def _write_file_chmod(path: Path, text: str, mode: int) -> None:
    if sys.platform == "win32":
        msg = f"Platform {sys.platform} does not support chmod, if this is a deployment it may be insecure."
        logger.warning(msg)
        path.write_text(text)
    else:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT, mode)
        with os.fdopen(fd, "w") as file:
            file.write(text)
