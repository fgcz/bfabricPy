from pydantic import BaseModel


class SubmittersSpec(BaseModel):
    # TODO
    submitters: dict[str, None]
