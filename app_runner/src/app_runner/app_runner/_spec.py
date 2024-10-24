from __future__ import annotations

import os
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


class MountOptions(BaseModel):
    work_dir_target: Path | None = None
    read_only: list[tuple[Path, Path]] = []
    share_bfabric_config: bool = True

    def collect(self, work_dir: Path):
        mounts = []
        if self.share_bfabric_config:
            mounts.append((Path("~/.bfabricpy.yml"), Path("/home/user/.bfabricpy.yml"), True))
        # TODO reconsider if we ever want work_dir_target to be customizable to be different from host path
        #      (currently things will break down if this is configured)
        work_dir_target = work_dir if self.work_dir_target is None else self.work_dir_target
        mounts.append((work_dir, work_dir_target, False))
        for source, target in self.read_only:
            mounts.append((source, target, True))
        return [(source.expanduser().absolute(), target, read_only) for source, target, read_only in mounts]


class CommandDocker(BaseModel):
    # TODO not sure if to call this "docker", since "docker-compatible" would be appropriate
    type: Literal["docker"] = "docker"
    image: str
    command: str
    entrypoint: str | None = None
    engine: str = "docker"
    env: dict[str, str] = {}
    mounts: MountOptions = MountOptions()

    def to_shell(self, work_dir: Path | None = None) -> list[str]:
        work_dir = (work_dir or Path("")).expanduser().absolute()
        mounts = self.mounts.collect(work_dir=work_dir)
        mount_args = []
        for host, container, read_only in mounts:
            source = shlex.quote(str(host))
            target = shlex.quote(str(container))
            mount_args.append("--mount")
            mount_args.append(f"type=bind,source={source},target={target}" + (",readonly" if read_only else ""))
        entrypoint_arg = ["--entrypoint", self.entrypoint] if self.entrypoint else []
        env_args = []
        for key, value in self.env.items():
            env_args.append("--env")
            env_args.append(f"{key}={shlex.quote(value)}")

        return [
            self.engine,
            "run",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--rm",
            *mount_args,
            *entrypoint_arg,
            *env_args,
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
