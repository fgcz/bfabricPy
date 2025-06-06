import os
import shlex
import subprocess
from pathlib import Path

from loguru import logger

from bfabric_app_runner.specs.app.commands_spec import CommandExec


def _get_shell_env(
    environ: dict[str, str] | None, config_env: dict[str, str], config_prepend_paths: list[Path]
) -> dict[str, str]:
    if environ is None:
        environ = os.environ.copy()

    if config_prepend_paths:
        # Ensure environ['PATH'] is set
        environ["PATH"] = environ.get("PATH", "")
        # Prepend paths
        for path in reversed(config_prepend_paths):
            resolved_path = path.expanduser().absolute()
            environ["PATH"] = f"{resolved_path}:{environ['PATH']}"

    for key, value in config_env.items():
        environ[key] = value

    return environ


def execute_command_exec(command: CommandExec, *args: str, environ: dict[str, str] | None = None) -> None:
    """Executes the command with the provided arguments."""
    command_args = shlex.split(command.command) + list(args)
    shell_env = _get_shell_env(environ, command.env, command.prepend_paths)
    logger.info("Executing command:", command_args)
    logger.debug(f"{command_args=}")
    logger.trace(f"{shell_env=}")
    subprocess.run(command_args, check=True, env=shell_env)
