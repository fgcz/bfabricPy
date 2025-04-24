from __future__ import annotations

import re
import secrets
from typing import Any

from loguru import logger
from mako.template import Template
from pydantic import BaseModel, field_validator, Field


class VariablesApp(BaseModel):
    """App specific variables that can be used in our config templates.

    They will be available as `${app.id}` etc. in the config files.
    """

    id: int
    name: str
    version: str

    @field_validator("name", mode="before")
    def validate_safe_name(cls, value: str) -> str:
        characters = re.compile(r"[^a-zA-Z0-9_-]+")
        return characters.sub("_", value)


class VariablesWorkunit(BaseModel):
    id: int
    file_token: str = Field(default_factory=lambda: secrets.token_hex(16))


class Variables(BaseModel):
    """Variables that can be used in our config templates."""

    app: VariablesApp
    workunit: VariablesWorkunit | None

    def as_dict(self) -> dict[str, VariablesApp | VariablesWorkunit | None]:
        return {"app": self.app, "workunit": self.workunit}


def interpolate_config_strings(data: Any, variables: Variables | dict[str, Any]) -> Any:
    """Recursively evaluates all strings in a data structure with Mako templates.

    This will not evaluate Mako templates in the YAML file itself, only in the individual strings.
    Since the current behavior is a subset of evaluating all strings in the YAML file, we could extend this later
    if it becomes necessary. However, it has the risk of making the config files more complex and should be avoided
    if possible.

    :param data: Any Python data structure (dict, list, str, etc.)
    :param variables: Template variables and their values
    :return: The data structure with all strings evaluated
    """
    variables = Variables.model_validate(variables) if isinstance(variables, dict) else variables
    logger.debug(f"Interpolating config strings with variables: {variables}")

    if isinstance(data, dict):
        return {key: interpolate_config_strings(value, variables) for key, value in data.items()}
    elif isinstance(data, list):
        return [interpolate_config_strings(item, variables) for item in data]
    elif isinstance(data, str):
        return str(Template(data).render(**variables.as_dict()))
    else:
        return data
