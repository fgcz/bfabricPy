from typing import Literal

from pydantic import BaseModel


class StaticYamlSpec(BaseModel):
    type: Literal["static_yaml"] = "static_yaml"

    data: dict | list
    """The YAML document content to write."""
    filename: str
    """The target filename to write to."""
