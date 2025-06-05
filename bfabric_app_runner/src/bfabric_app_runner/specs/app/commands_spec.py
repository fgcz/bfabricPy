import os
import shlex
import sys
from pathlib import Path
from typing import Literal, Annotated, Any

from pydantic import BaseModel, Discriminator, ConfigDict, field_validator
from pydantic_core.core_schema import ValidationInfo


class CommandShell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # TODO: Now deprecated by exec type - we can add a "bash" type later, if needed
    type: Literal["shell"] = "shell"
    """Identifies the command type."""

    command: str
    """The command to run, will be split by spaces and is not an actual shell script."""

    def to_shell(self) -> list[str]:
        """Returns a shell command that can be used to run the specified command."""
        return shlex.split(self.command)

    def to_shell_env(self, environ: dict[str, str] | None) -> dict[str, str]:
        """Returns the shell environment variables to set before executing the command."""
        return environ if environ is not None else os.environ.copy()


class CommandExec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["exec"] = "exec"
    """Identifies the command type."""

    command: str
    """The command to run, will be split by `shlex.split` and is not an actual shell script."""

    env: dict[str, str] = {}
    """Environment variables to set before executing the command."""

    prepend_paths: list[Path] = []
    """A list of paths to prepend to the PATH variable before executing the command.

    If multiple paths are specified, the first one will be the first in PATH, etc.
    """

    def to_shell(self) -> list[str]:
        """Returns a shell command that can be used to run the specified command."""
        return shlex.split(self.command)

    def to_shell_env(self, environ: dict[str, str] | None) -> dict[str, str]:
        """Returns the shell environment variables to set before executing the command."""
        if environ is None:
            environ = os.environ.copy()

        if self.prepend_paths:
            # Ensure environ['PATH'] is set
            environ["PATH"] = environ.get("PATH", "")
            # Prepend paths
            for path in reversed(self.prepend_paths):
                resolved_path = path.expanduser().absolute()
                environ["PATH"] = f"{resolved_path}:{environ['PATH']}"

        for key, value in self.env.items():
            environ[key] = value

        return environ


class MountOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # TODO this will have to be reworked later it is not flexible enough as it does not allow to specify the
    #      flags for shared etc.
    work_dir_target: Path | None = None
    read_only: list[tuple[Path, Path]] = []
    writeable: list[tuple[Path, Path]] = []
    share_bfabric_config: bool = True

    def collect(self, work_dir: Path) -> list[tuple[Path, Path, bool]]:
        """Collects all mounts that are required to run the command.

        These are returned as triplets of (source, target, read_only).
        """
        mounts = []
        if self.share_bfabric_config:
            mounts.append((Path("~/.bfabricpy.yml"), Path("/home/user/.bfabricpy.yml"), True))
        # TODO reconsider if we ever want work_dir_target to be customizable to be different from host path
        #      (currently things will break down if this is configured)
        work_dir_target = work_dir if self.work_dir_target is None else self.work_dir_target
        mounts.append((work_dir, work_dir_target, False))
        for source, target in self.read_only:
            mounts.append((source, target, True))
        for source, target in self.writeable:
            mounts.append((source, target, False))
        return [(source.expanduser().absolute(), target, read_only) for source, target, read_only in mounts]


class CommandDocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # TODO not sure if to call this "docker", since "docker-compatible" would be appropriate
    type: Literal["docker"] = "docker"
    """Identifies the command type."""
    image: str
    """The container image to run."""
    command: str
    """The command to execute in the container."""
    entrypoint: str | None = None
    """The entrypoint to use for the container (instead of the image's default)."""
    engine: Literal["docker", "podman"] = "docker"
    """The container engine to use."""
    env: dict[str, str] = {}
    """Environment variables to set in the container."""
    mac_address: str | None = None
    """The MAC address to use for the container (instead of Docker's default assignment)."""
    mounts: MountOptions = MountOptions()
    """Mount options for the container."""
    hostname: str | None = None
    """The hostname to use for the container (instead of Docker's default assignment)."""
    custom_args: list[str] = []
    """Any custom CLI arguments to pass to the container engine."""

    def to_shell(self, work_dir: Path | None = None) -> list[str]:
        """Returns a shell command that can be used to run the specified command."""
        work_dir = (work_dir or Path()).expanduser().absolute()
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
        mac_address_arg = ["--mac-address", self.mac_address] if self.mac_address else []
        hostname_arg = ["--hostname", self.hostname] if self.hostname else []

        return [
            self.engine,
            "run",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--rm",
            *mount_args,
            *entrypoint_arg,
            *env_args,
            *mac_address_arg,
            *self.custom_args,
            *hostname_arg,
            self.image,
            *shlex.split(self.command),
        ]

    def to_shell_env(self, environ: dict[str, str] | None = None) -> dict[str, str]:
        """Returns the shell environment variables to set before executing the command."""
        return environ if environ is not None else os.environ.copy()


class CommandAppZip(BaseModel):
    type: Literal["app.zip"] = "app.zip"

    app_zip: Path
    """The path to the app.zip file that contains the relevant code."""
    app_name: str
    """The app name, will be used to construct module path by default."""
    purpose: Literal["dispatch", "process", "collect"]
    """The purpose of this command, will be populated automatically by putting it into the CommandsSpec."""

    def to_shell(self, work_dir: Path | None = None) -> list[str]:
        # TODO
        execute_app_zip_bin = [sys.executable, "-m", "bfabric_app_runner.___"]
        module_path = f"{self.app_name}.integrations.bfabric.{self.purpose}"
        [execute_app_zip_bin, "python", "-m", module_path]
        raise NotImplementedError

    def to_shell_env(self, environ: dict[str, str] | None = None) -> dict[str, str]:
        """Returns the shell environment variables to set before executing the command."""
        return environ if environ is not None else os.environ.copy()


Command = Annotated[CommandShell | CommandExec | CommandDocker | CommandAppZip, Discriminator("type")]


class CommandsSpec(BaseModel):
    """Defines the commands that are required to execute an app."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    dispatch: Command
    """The app dispatch command.

    It will be called with arguments: `$workunit_ref` `$work_dir`.
    """

    process: Command
    """The app process command.

    It will be called with arguments: `$chunk_dir`.
    """

    collect: Command | None = None
    """The app collect command, can be omitted if your process command already creates an `outputs.yml` file.

    It will be called with arguments: `$workunit_ref` `$chunk_dir`.
    """

    @field_validator("dispatch", "process", "collect", mode="before")
    def populate_command_app_zip_purpose(cls, value: Any, info: ValidationInfo) -> Any:
        """Automatically sets the _purpose field for CommandAppZip instances based on the field name."""
        if isinstance(value, dict) and value.get("type") == "app.zip":
            value["purpose"] = info.field_name
        elif isinstance(value, CommandAppZip):
            expected_purpose = info.field_name
            if value.purpose != expected_purpose:
                raise ValueError(f"Inconsistent purpose {value.purpose!r} expected {expected_purpose!r}")
        return value
