import importlib.resources
import sys
from pathlib import Path

import packaging.version
from loguru import logger

from bfabric_app_runner.specs.app.app_spec import BfabricAppSpec


def _is_valid_version(version: str) -> bool:
    """Returns True if the version string is a valid Python package version."""
    try:
        packaging.version.Version(version)
        return True
    except packaging.version.InvalidVersion:
        return False


def get_app_runner_dep_string(version: str) -> str:
    """Returns a formatted version string that can be used with uv.

    For example:
    - "bfabric-app-runner==1.2.3" for PyPI versions
    - "bfabric-app-runner@git+https://..." for git references
    """
    pypi_package = "bfabric-app-runner"
    dep_type = "==" if _is_valid_version(version) else "@"
    return f"{pypi_package}{dep_type}{version}"


def render_makefile_template(
    template: str, app_runner_dep_string: str, python_version: str, use_external_runner: bool = False
) -> str:
    """Renders the workunit template by interpolating the specified values."""
    # For makefile escaping of URIs containing `#` character is required
    app_runner_dep_string = app_runner_dep_string.replace(r"#", r"\#")

    makefile = template.replace("@APP_RUNNER_DEP_STRING@", app_runner_dep_string)
    makefile = makefile.replace("@PYTHON_VERSION@", python_version)
    makefile = makefile.replace("@USE_EXTERNAL_RUNNER@", "true" if use_external_runner else "false")
    return makefile


def render_makefile(
    path: Path,
    bfabric_app_spec: BfabricAppSpec,
    rename_existing: bool,
    *,
    python_version: str | None = None,
    use_external_runner: bool = False,
) -> None:
    """Render the workunit Makefile to `path` using information from the app spec."""
    app_runner_dep_string = get_app_runner_dep_string(version=bfabric_app_spec.app_runner)
    if python_version is None:
        python_version = f"{sys.version_info[0]}.{sys.version_info[1]}"
    template = importlib.resources.read_text("bfabric_app_runner", "resources/workunit.mk")
    makefile = render_makefile_template(
        template=template,
        app_runner_dep_string=app_runner_dep_string,
        python_version=python_version,
        use_external_runner=use_external_runner,
    )
    if path.exists() and rename_existing:
        logger.info("Renaming existing Makefile to Makefile.bak")
        path.rename(path.parent / "Makefile.bak")
    path.write_text(makefile)
    logger.success(f"Writing Makefile to {path}")
