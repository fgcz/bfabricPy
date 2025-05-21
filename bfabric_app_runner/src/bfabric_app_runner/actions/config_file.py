from pathlib import Path
from typing import Any

import yaml
from glom import glom
from loguru import logger

from pydantic import BaseModel, field_validator, model_validator


class ActionConfig(BaseModel):
    """Configuration which will be passed to the corresponding action."""

    work_dir: Path | None = None
    app_ref: Path | str | None = None
    workunit_ref: int | Path | None = None
    ssh_user: str | None = None
    filter: str | None = None
    force_storage: Path | None = None
    read_only: bool | None = None

    @field_validator("app_ref", mode="after")
    @classmethod
    def ensure_app_ref_path_if_path(cls, app_ref: Path | str) -> Path | str:
        if Path(app_ref).exists():
            return Path(app_ref)
        return app_ref


class FromConfigFile(BaseModel):
    config: Path | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_config_file(cls, values: Any) -> Any:
        if isinstance(values, dict) and "config" in values and values["config"] is not None:
            logger.debug(f"Parsing config file: {values['config']}")
            with Path(values["config"]).open("r") as config_file:
                config_data = yaml.safe_load(config_file)
            config_entry = glom(config_data, "bfabric_app_runner.action")
            data = ActionConfig.model_validate(config_entry)

            # update all values which are not provided explicitly with the values from config_parsed
            for key, value in data:
                if key not in values and value is not None:
                    logger.debug(f"Overriding {key} with value from config file: {value}")
                    values[key] = value

        return values
