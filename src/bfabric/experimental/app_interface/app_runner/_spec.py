import shlex
from typing import Literal, Annotated, Union

from pydantic import BaseModel, Discriminator


# TODO: This is kept very simple for now, so that it could be easily extended in the future.


class CommandShell(BaseModel):
    type: Literal["shell"] = "shell"
    command: str

    def to_shell(self) -> list[str]:
        return shlex.split(self.command)


class CommandDocker(BaseModel):
    type: Literal["docker"] = "docker"
    image: str
    command: str
    mount_dirs_readonly: list[tuple[str, str]] = []

    def to_shell(self) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            *[
                f"--mount type=bind,source={host},target={container},readonly"
                for host, container in self.mount_dirs_readonly
            ],
            self.image,
            *shlex.split(self.command),
        ]


Command = Annotated[Union[CommandShell, CommandDocker], Discriminator("type")]


class CommandsSpec(BaseModel):
    dispatch: Command
    process: Command
    collect: Command


class AppSpec(BaseModel):
    commands: CommandsSpec
    # Note: While we use the old submitter, this is still necessary
    reuse_default_resource: bool = True
