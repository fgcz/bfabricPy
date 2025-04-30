import importlib.metadata
import importlib.resources
from pathlib import Path

from loguru import logger

from bfabric.config.config_data import ConfigData, export_config_data
from bfabric_app_runner.cli.app import _write_file_chmod


def copy_dev_makefile(work_dir: Path, config_data: ConfigData, create_env_file: bool) -> None:
    """Copies the workunit.mk file to the work directory, and sets the version of the app runner.

    It also creates a .env file containing the BFABRICPY_CONFIG_OVERRIDE environment variable containing the configured
    connection. For security reasons it will be chmod 600.
    """
    with importlib.resources.path("bfabric_app_runner", "resources/workunit.mk") as source_path:
        target_path = work_dir / "Makefile"

        makefile_template = source_path.read_text()
        app_runner_version = importlib.metadata.version("bfabric_app_runner")
        makefile = makefile_template.replace("@RUNNER_VERSION@", app_runner_version)

        if target_path.exists():
            logger.info("Renaming existing Makefile to Makefile.bak")
            target_path.rename(work_dir / "Makefile.bak")
        logger.info(f"Copying Makefile from {source_path} to {target_path}")
        target_path.parent.mkdir(exist_ok=True, parents=True)
        target_path.write_text(makefile)

    if create_env_file:
        json_string = export_config_data(config_data)
        env_file_content = f'BFABRICPY_CONFIG_OVERRIDE="{json_string.replace('"', '\\"')}"\n'
        env_file_path = work_dir / ".env"
        if env_file_path.exists():
            logger.info("Renaming existing .env file to .env.bak")
            env_file_path.rename(work_dir / ".env.bak")
        logger.info(f"Creating .env file at {env_file_path}")
        _write_file_chmod(path=env_file_path, text=env_file_content, mode=0o600)
