import os
import shlex
import subprocess
from pathlib import Path

from loguru import logger

from bfabric_app_runner.errors import CommandFailedError
from bfabric_app_runner.specs.app.commands_spec import CommandExec


def log_command_output(level: str, output: str) -> None:
    """Emits each line of ``output`` as its own record; one multi-line record would prefix only its first."""
    if not output.strip():
        return
    for line in output.splitlines():
        logger.log(level, line)


def _get_shell_env(
    environ: dict[str, str] | None, config_env: dict[str, str], config_prepend_paths: list[Path]
) -> dict[str, str]:
    # Copying is load-bearing: neither os.environ nor a caller-supplied dict may be mutated.
    environ = os.environ.copy() if environ is None else dict(environ)
    for path in reversed(config_prepend_paths):
        environ["PATH"] = f"{path.expanduser().absolute()}:{environ.get('PATH', '')}"
    return environ | config_env


def execute_command_exec(
    command: CommandExec,
    *args: str,
    environ: dict[str, str] | None = None,
    log_output_level: str | None = None,
) -> None:
    """Executes the command with the provided arguments.

    :param log_output_level: when set (e.g. ``"DEBUG"``), the command's stdout/stderr is captured and
        re-emitted through the logger at this level. ``None`` inherits the parent's streams so output is
        shown directly (the right choice for the app's own output); a level is used for noisy
        provisioning steps whose output only matters when debugging.
    """
    command_args = shlex.split(command.command) + list(args)
    shell_env = _get_shell_env(environ, command.env, command.prepend_paths)
    logger.info(f"Executing command: {shlex.join(command_args)}")
    logger.debug(f"{command_args=}")
    logger.trace(f"{shell_env=}")
    if log_output_level is None:
        try:
            subprocess.run(command_args, check=True, env=shell_env)  # pyright: ignore[reportUnusedCallResult]
        except subprocess.CalledProcessError as error:
            raise CommandFailedError(command_args, error.returncode) from error
        return

    # Capture output (stderr merged into stdout to preserve ordering) and route it through the logger.
    proc = subprocess.run(
        command_args, env=shell_env, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    if proc.returncode != 0:
        log_command_output("ERROR", proc.stdout)
        raise CommandFailedError(command_args, proc.returncode)
    log_command_output(log_output_level, proc.stdout)
