from enum import Enum
from pathlib import Path
from typing import Literal, Annotated, Any

import yaml
from glom import glom
from loguru import logger
from pydantic import BaseModel, Field, model_validator, field_validator


class Action(str, Enum):
    run = "run"
    dispatch = "dispatch"
    inputs = "inputs"
    process = "process"
    outputs = "outputs"


class ActionConfig(BaseModel):
    """Configuration which will be passed to the corresponding action."""

    work_dir: Path | None = None
    app_ref: Path | str | None = None
    workunit_ref: int | Path | None = None
    ssh_user: str | None = None
    filter: str | None = None
    force_storage: Path | None = None

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
        if isinstance(values, dict) and "config" in values:
            logger.debug(f"Parsing config file: {values['config']}")
            with Path(values["config"]).open("r") as config_file:
                config_data = yaml.safe_load(config_file)

            # TODO make safer (glom?)
            config_entry = glom(config_data, "bfabric_app_runner.action")

            # TODO test this scenario
            data = ActionConfig.model_validate(config_entry)

            # update all values which are not provided explicitly with the values from config_parsed
            for key, value in data:
                if key not in values and value is not None:
                    logger.debug(f"Overriding {key} with value from config file: {value}")
                    values[key] = value

        return values


class ActionDispatch(FromConfigFile):
    action: Literal[Action.dispatch] = Action.dispatch
    work_dir: Path
    app_ref: Path | str
    workunit_ref: int | Path


#    @model_validator(mode="before")
#    @classmethod
#    def parse_config_file(cls, values: Any) -> Any:
#        # smarter version using this model
#        if isinstance(values, dict) and "config" in values:
#            logger.debug(f"Parsing config file: {values['config']}")
#            with Path(values["config"]).open("r") as config_file:
#                config_data = yaml.safe_load(config_file)
#
#            # TODO make safer (glom?)
#            config_entry = config_data["bfabric_app_runner"]["action"]
#
#            # TODO test this scenario
#            if "config" in config_entry:
#                logger.info("Recursion detected: config file cannot contain another config file.")
#                raise ValueError("Recursion detected: config file cannot contain another config file.")
#
#            logger.info("Parsing config file: %s", config_entry)
#            # TODO this validation step fails because of missing parameters right now -> how to do this
#            config_parsed = ActionDispatch.model_validate(config_data)
#            logger.info("Finished parsing config file: %s", config_parsed)
#
#            # update all values which are not provided explicitly with the values from config_parsed
#            logger.info("x")
#            for key, value in config_parsed:
#                if key not in values:
#                    logger.debug(f"Overriding {key} with value from config file: {value}")
#                    values[key] = value
#                else:
#                    logger.debug(f"Keeping {key} with value from command line: {values[key]}")
#
#        return values


# @model_validator(mode="before")
# @classmethod
# def parse_config_file(cls, values: Any) -> Any:
#    # Naive hardcoded version
#    if isinstance(values, dict) and "config" in values:
#        with Path(values["config"]).open("r") as config_file:
#            config_data = yaml.safe_load(config_file)
#        values_new = values.copy()
#        values_new["app_ref"] = config_data["bfabric_app_runner"]["action"]["app_ref"]
#        try:
#            values_new["app_ref"] = Path(values_new["app_ref"])
#        except TypeError:
#            pass
#        values_new["workunit_ref"] = config_data["bfabric_app_runner"]["action"]["workunit_ref"]
#        return values_new
#    return values


class ActionRun(FromConfigFile):
    action: Literal[Action.run] = Action.run
    work_dir: Path
    chunk: str | None = None
    ssh_user: str | None = None
    filter: str | None = None
    app_ref: Path | str
    force_storage: Path | None = None


class ActionInputs(FromConfigFile):
    action: Literal[Action.inputs] = Action.inputs
    work_dir: Path
    chunk: str | None = None
    ssh_user: str | None = None
    filter: str | None = None


class ActionProcess(FromConfigFile):
    action: Literal[Action.process] = Action.process
    work_dir: Path
    app_ref: Path | str
    chunk: str | None = None


class ActionOutputs(FromConfigFile):
    action: Literal[Action.outputs] = Action.outputs
    work_dir: Path
    workunit_ref: int | Path
    app_ref: Path | str
    chunk: str | None = None
    ssh_user: str | None = None
    force_storage: Path | None = None


ActionGeneric = Annotated[
    ActionRun | ActionDispatch | ActionInputs | ActionProcess | ActionOutputs, Field(discriminator="action")
]
