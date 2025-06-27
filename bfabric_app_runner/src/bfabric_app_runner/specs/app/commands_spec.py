from pathlib import Path
from typing import Literal, Annotated

from pydantic import BaseModel, Discriminator, ConfigDict


class CommandShell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # TODO: Now deprecated by exec type - we can add a "bash" type later, if needed
    type: Literal["shell"] = "shell"
    """Identifies the command type."""

    command: str
    """The command to run, will be split by spaces and is not an actual shell script."""


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


class MountOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_dir_target: Path | None = None
    read_only: list[tuple[Path, Path]] = []
    writeable: list[tuple[Path, Path]] = []
    share_bfabric_config: bool = True


class CommandDocker(BaseModel):
    model_config = ConfigDict(extra="forbid")
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


class CommandPythonEnv(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["python_env"] = "python_env"

    pylock: Path
    """Path to the Pylock file that specifies the environment to use."""

    command: str
    """The command to run, will be split by `shlex.split` and is not an actual shell script."""

    python_version: str | None = None
    """The Python version to use."""

    local_extra_deps: list[Path] = []
    """Additional dependencies to install into the environment.

    Each entry should be a path to a wheel, sdist, or local package directory.
    These will be installed into the environment with `uv pip install --no-deps` after the main requirements.
    No dependency resolution will be performed for these, so their dependencies should already be present
    in the environment (typically specified in the pylock file).
    """

    env: dict[str, str] = {}
    """Environment variables to set before executing the command."""

    prepend_paths: list[Path] = []
    """A list of paths to prepend to the PATH variable before executing the command.

    If multiple paths are specified, the first one will be the first in PATH, etc.
    """

    refresh: bool = False
    """When True, forces re-download and cache refresh of the environment, ignoring any existing cache."""


Command = Annotated[CommandShell | CommandExec | CommandDocker | CommandPythonEnv, Discriminator("type")]


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
