from typing import Annotated

from pydantic import BaseModel, StringConstraints


class SubmitterRef(BaseModel):
    """Reference of a submitter and potential configuration overrides."""

    name: str
    params: dict[Annotated[str, StringConstraints(pattern="^--.*")], str | None] = {}
