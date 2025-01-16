from pydantic import BaseModel, constr


class SubmitterRef(BaseModel):
    """Reference of a submitter and potential configuration overrides."""

    name: str
    params: dict[constr(pattern="^--.*"), str | None]
