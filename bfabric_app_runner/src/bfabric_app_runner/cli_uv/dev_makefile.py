import importlib.metadata
import importlib.resources
from pathlib import Path

from loguru import logger


def _render_makefile(template_variables: dict[str, str]) -> str:
    with importlib.resources.path("bfabric_app_runner", "resources/workunit.mk") as source_path:
        logger.info(f"Rendering Makefile template from {source_path} with variables: {template_variables!r}")
        makefile = source_path.read_text()
        for key, value in template_variables.items():
            makefile = makefile.replace(f"@{key}@", value)
        return makefile


def write_dev_makefile(
    #    work_dir: Path, app_definition: Path | str, config_data: ConfigData, create_env_file: bool
    work_dir: Path,
    env_data: dict[str, str],
) -> None:
    """Copies the workunit.mk file to the work directory, and sets the version of the app runner.

    It also creates a .env file containing the BFABRICPY_CONFIG_OVERRIDE environment variable containing the configured
    connection. For security reasons it will be chmod 600.
    """
    makefile = _render_makefile(template_variables=env_data)
    target_path = work_dir / "Makefile"
    if target_path.exists():
        logger.info("Renaming existing Makefile to Makefile.bak")
        target_path.rename(work_dir / "Makefile.bak")
    logger.info(f"Writing rendered Makefile to {target_path}")
    target_path.parent.mkdir(exist_ok=True, parents=True)
    target_path.write_text(makefile)
