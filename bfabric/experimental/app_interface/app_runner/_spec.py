from pydantic import BaseModel

# TODO: This is kept very simple for now, so that it could be easily extended in the future.


class CommandsSpec(BaseModel):
    dispatch: str
    process: str


class AppSpec(BaseModel):
    commands: CommandsSpec
