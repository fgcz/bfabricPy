from pathlib import Path
import shlex
import os
from bfabric_app_runner.commands.command_exec import execute_command_exec
from bfabric_app_runner.specs.app.commands_spec import CommandExec, CommandDocker, MountOptions


def _collect_mount_options(options: MountOptions, work_dir: Path) -> list[tuple[Path, Path, bool]]:
    """Collects all mounts that are required to run the command.

    These are returned as triplets of (source, target, read_only).
    """
    mounts = []
    if options.share_bfabric_config:
        mounts.append((Path("~/.bfabricpy.yml"), Path("/home/user/.bfabricpy.yml"), True))
    # TODO reconsider if we ever want work_dir_target to be customizable to be different from host path
    #      (currently things will break down if this is configured)
    work_dir_target = work_dir if options.work_dir_target is None else options.work_dir_target
    mounts.append((work_dir, work_dir_target, False))
    for source, target in options.read_only:
        mounts.append((source, target, True))
    for source, target in options.writeable:
        mounts.append((source, target, False))
    return [(source.expanduser().absolute(), target, read_only) for source, target, read_only in mounts]


def _to_shell(command: CommandDocker, work_dir: Path | None = None) -> list[str]:
    """Returns a shell command that can be used to run the specified command."""
    work_dir = (work_dir or Path()).expanduser().absolute()
    mounts = _collect_mount_options(command.mounts, work_dir)
    mount_args = []
    for host, container, read_only in mounts:
        source = shlex.quote(str(host))
        target = shlex.quote(str(container))
        mount_args.append("--mount")
        mount_args.append(f"type=bind,source={source},target={target}" + (",readonly" if read_only else ""))
    entrypoint_arg = ["--entrypoint", command.entrypoint] if command.entrypoint else []
    env_args = []
    for key, value in command.env.items():
        env_args.append("--env")
        env_args.append(f"{key}={shlex.quote(value)}")
    mac_address_arg = ["--mac-address", command.mac_address] if command.mac_address else []
    hostname_arg = ["--hostname", command.hostname] if command.hostname else []

    return [
        command.engine,
        "run",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--rm",
        *mount_args,
        *entrypoint_arg,
        *env_args,
        *mac_address_arg,
        *command.custom_args,
        *hostname_arg,
        command.image,
        *shlex.split(command.command),
    ]


def execute_command_docker(command: CommandDocker, *args: str) -> None:
    """Executes the command with the provided arguments."""
    shell_command = _to_shell(command)
    execute_command_exec(CommandExec(command=shlex.join(shell_command)), *args)
