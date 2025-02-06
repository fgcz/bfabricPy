from typing import Any

from pydantic import BaseModel


class SubmitterRef(BaseModel):
    """Reference of a submitter and potential configuration overrides."""

    name: str
    config: dict[str, Any] = {}
