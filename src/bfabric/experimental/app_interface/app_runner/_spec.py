from __future__ import annotations
import shlex
from pathlib import Path
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
    work_dir_mount: str = "/work"
    mount_dirs_readonly: list[tuple[str, str]] = []

    def to_shell(self, work_dir: Path | None = None) -> list[str]:
        work_dir = (work_dir or Path(".")).absolute()
        return [
            "docker",
            "run",
            "--rm",
            f"--mount type=bind,source={shlex.quote(str(work_dir))},target={shlex.quote(self.work_dir_mount)}",
            *[
                f"--mount type=bind,source={shlex.quote(host)},target={shlex.quote(container)},readonly"
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
