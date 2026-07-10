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


def execute_command_exec(
    command: CommandExec,
    *args: str,
    environ: dict[str, str] | None = None,
    log_output_level: str | None = None,
) -> None:
    """Executes the command with the provided arguments.

    :param log_output_level: when set (e.g. ``"DEBUG"``), the command's stdout/stderr is captured and
        re-emitted through the logger at this level instead of inheriting the parent's streams. ``None``
        inherits the parent's stdout/stderr so output is shown directly (the right choice for the app's own
        output); a level is used for noisy provisioning steps whose output only matters when debugging.
    """
    command_args = shlex.split(command.command) + list(args)
    shell_env = _get_shell_env(environ, command.env, command.prepend_paths)
    logger.info(f"Executing command: {shlex.join(command_args)}")
    logger.debug(f"{command_args=}")
    logger.trace(f"{shell_env=}")
    if log_output_level is None:
        subprocess.run(command_args, check=True, env=shell_env)  # pyright: ignore[reportUnusedCallResult]
        return

    # Capture output (stderr merged into stdout to preserve ordering) and route it through the logger.
    proc = subprocess.run(
        command_args, env=shell_env, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    if proc.returncode != 0:
        logger.error(f"Command failed with exit code {proc.returncode}: {shlex.join(command_args)}\n{proc.stdout}")
        raise subprocess.CalledProcessError(proc.returncode, command_args, output=proc.stdout)
    if proc.stdout.strip():
        logger.log(log_output_level, f"Command output:\n{proc.stdout}")
