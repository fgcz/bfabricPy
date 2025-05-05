import os
import sys
import typing
from pathlib import Path
from collections.abc import Generator

import yaml
from loguru import logger

from bfabric.config.config_data import ConfigData, export_config_data


def _export_env_data(
    config_data: ConfigData | None,
    app_spec: Path | str,
    workunit_ref: Path,
    uv_bin: Path,
    python_version: str,
) -> dict[str, str]:
    """Renders the environment variables as they should be exported to the .env file."""
    app_spec_str = app_spec if isinstance(app_spec, str) else str(app_spec.resolve())
    data = {
        "APP_RUNNER_APP_SPEC": app_spec_str,
        "APP_RUNNER_WORKUNIT_REF": str(workunit_ref.resolve()),
        "APP_RUNNER_UV_BIN": str(uv_bin.resolve()),
        "PYTHON_VERSION": python_version,
    }
    if config_data is not None:
        config_data_json = export_config_data(config_data)
        data["BFABRICPY_CONFIG_OVERRIDE"] = config_data_json.replace('"', '\\"')


def _write_dot_env_file(file: Path, env_data: dict[str, str]) -> None:
    content = "\n".join(f"{key}={value}" for key, value in env_data.items()) + "\n"
    with _open_scope_limited_write_file(file) as fh:
        fh.write(content)


def _write_env_yaml_file(file: Path, env_data: dict[str, str]) -> None:
    with _open_scope_limited_write_file(file) as fh:
        yaml.safe_dump(env_data, fh)


def write_env_data(
    work_dir: Path, config_data: ConfigData, app: Path | str, workunit: Path, uv_bin: Path, python_version: str
) -> dict[str, str]:
    """Writes environment data for `work_dir` and returns it."""
    env_data = _export_env_data(
        config_data=config_data, app_spec=app, workunit_ref=workunit, uv_bin=uv_bin, python_version=python_version
    )
    # TODO in a second step we can harmonize and simplify this, e.g. we could make a python script which prints bash
    #    exports for the config in the yaml directly. But the main reason I won't implement it just now is that it's not
    #    clear how to handle BFABRICPY_CONFIG_OVERRIDE string conversion (str vs dict)
    _write_dot_env_file(file=work_dir / ".env", env_data=env_data)
    _write_env_yaml_file(file=work_dir / "env.yml", env_data=env_data)
    return env_data


def _open_scope_limited_write_file(path: Path, *, chmod_value: int = 0o600) -> Generator[typing.TextIO, None, None]:
    if sys.platform == "win32":
        msg = f"Platform {sys.platform} does not support chmod, if this is a deployment it may be insecure."
        logger.warning(msg)
        with path.open("w") as file:
            yield file
    else:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT, chmod_value)
        with os.fdopen(fd, "w") as file:
            yield file
