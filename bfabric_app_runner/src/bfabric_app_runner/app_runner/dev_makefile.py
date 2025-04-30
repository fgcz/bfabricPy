import importlib.metadata
import importlib.resources
from pathlib import Path

from loguru import logger

from bfabric.config.config_data import ConfigData, export_config_data
from bfabric_app_runner.cli.app import _write_file_chmod


def _render_makefile(app_def: Path | str) -> str:
    template_variables = {
        "RUNNER_VERSION": importlib.metadata.version("bfabric_app_runner"),
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
