from typing import Annotated

from pydantic import BaseModel, StringConstraints


class SlurmSubmitterParams(BaseModel):
    params: dict[Annotated[str, StringConstraints(pattern="^--.*")], str | None]
