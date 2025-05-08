from __future__ import annotations
from pathlib import Path  # noqa

import yaml
from pydantic import BaseModel, Field, AliasChoices

from bfabric.config.config_data import ConfigData  # noqa


class EnvData(BaseModel):
    app_spec: Path | str = Field(..., validation_alias=AliasChoices("app_spec", "APP_RUNNER_APP_SPEC"))
    workunit_ref: Path = Field(..., validation_alias=AliasChoices("workunit_ref", "APP_RUNNER_WORKUNIT_REF"))
    uv_bin: Path = Field(..., validation_alias=AliasChoices("uv_bin", "APP_RUNNER_UV_BIN"))
    uv_python_version: str = Field(
        ..., validation_alias=AliasChoices("uv_python_version", "APP_RUNNER_UV_PYTHON_VERSION")
    )
    deps_string: str = Field(..., validation_alias=AliasChoices("deps_string", "APP_RUNNER_UV_DEPS_STRING"))
    config_data: ConfigData | None = Field(
        ..., validation_alias=AliasChoices("config_data", "BFABRICPY_CONFIG_OVERRIDE")
    )

    @classmethod
    def load_yaml(cls, file: Path) -> EnvData:
        """Loads the env data from the provided yaml file."""
        with file.open(mode="r") as fh:
            return cls.model_validate(yaml.safe_load(fh))

    def save_yaml(self, file: Path) -> None:
        """Writes the env data to the specified yaml file."""
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open(mode="w") as fh:
            yaml.safe_dump(self.model_dump(mode="json"), fh)


def env_data_from_cli(
    app_spec: Path | str,
    workunit_ref: Path,
    uv_bin: Path,
    uv_python_version: str,
    deps_string: str,
    config_data: ConfigData | None,
) -> EnvData:
    """Initializes EnvData from CLI arguments, mainly resolving paths to absolute paths."""
    return EnvData(
        app_spec=app_spec if isinstance(app_spec, str) else str(app_spec.resolve()),
        workunit_ref=workunit_ref.resolve(),
        uv_bin=uv_bin.resolve(),
        uv_python_version=uv_python_version,
        deps_string=deps_string,
        config_data=config_data,
    )
