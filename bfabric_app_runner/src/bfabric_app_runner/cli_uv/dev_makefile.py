import importlib.metadata
import importlib.resources
from pathlib import Path
from typing import Literal

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
    # makefile = _render_makefile(template_variables=env_data)

    makefile = importlib.resources.read_text("bfabric_app_runner", "resources/workunit_new.mk")

    target_path = work_dir / "Makefile"
    if target_path.exists():
        logger.info("Renaming existing Makefile to Makefile.bak")
        target_path.rename(work_dir / "Makefile.bak")
    logger.info(f"Writing rendered Makefile to {target_path}")
    target_path.parent.mkdir(exist_ok=True, parents=True)
    target_path.write_text(makefile)


def format_env_data(env_data: dict[str, str], format: Literal["bash", "fish", "makefile"]) -> str:
    """
    Format environment variables for different shells or Makefile.

    Args:
        env_data: Dictionary of environment variables (key-value pairs)
        format: The target format ("bash", "fish", or "makefile")

    Returns:
        A string with formatted environment variable declarations
    """
    result = []

    if format == "bash":
        for key, value in env_data.items():
            # Use double quotes and escape any internal double quotes
            escaped_value = value.replace('"', '\\"')
            result.append(f'export {key}="{escaped_value}"')
    elif format == "fish":
        for key, value in env_data.items():
            # For fish, we need to escape single quotes and backslashes
            escaped_value = value.replace("\\", "\\\\").replace("'", "\\'")
            result.append(f"set -x {key} '{escaped_value}'")
    elif format == "makefile":
        # For makefiles, values with spaces need quotes
        for key, value in env_data.items():
            if " " in value or "\t" in value or "\n" in value or any(c in value for c in "$()"):
                result.append(f'{key} := "{value.replace('"', '\\"')}"')
            else:
                result.append(f"{key} := {value}")
    else:
        raise ValueError(f"Unsupported format: {format}")

    return "\n".join(result)
