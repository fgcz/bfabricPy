from pydantic import BaseModel

# TODO: This is kept very simple for now, so that it could be easily extended in the future.


class CommandsSpec(BaseModel):
    dispatch: str
    process: str
    collect: str


class AppSpec(BaseModel):
    version: list[str] = []
    commands: CommandsSpec
    # Note: While we use the old submitter, this is still necessary
    reuse_default_resource: bool = True
