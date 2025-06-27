import hashlib
import os
import shlex
from pathlib import Path

from bfabric_app_runner.commands.command_exec import execute_command_exec
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


def _get_app_runner_cache_path(command: CommandPythonEnv) -> Path:
    """Get the app_runner cache directory for Python environments."""
    # Determine the cache directory
    cache_dir = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser()
    app_runner_cache = cache_dir / "bfabric_app_runner" / "envs"

    # Get the env path inside this directory
    env_hash = _compute_env_hash(command)
    return app_runner_cache / env_hash


def _compute_env_hash(command: CommandPythonEnv) -> str:
    """Returns a hash for the environment based on the command's specifications."""
    hash_input = f"{command.python_version or 'default'}:{command.pylock.absolute()}"
    if command.local_extra_deps:
        deps_str = ",".join(str(p.absolute()) for p in command.local_extra_deps)
        hash_input += f":{deps_str}"
    env_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    return env_hash


def _provision_environment(command: CommandPythonEnv) -> None:
    """Provision the Python environment using uv venv."""
    env_path = _get_app_runner_cache_path(command)
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the virtual environment using uv venv
    venv_cmd = ["uv", "venv", "-p", command.python_version, str(env_path)]

    exec_command = CommandExec(command=shlex.join(venv_cmd), env=command.env, prepend_paths=command.prepend_paths)
    execute_command_exec(exec_command)

    # Install dependencies from pylock file
    python_executable = env_path / "bin" / "python"
    install_cmd = ["uv", "pip", "install", "-p", str(python_executable), "-r", str(command.pylock)]

    if command.refresh:
        install_cmd.append("--reinstall")

    if command.local_extra_deps:
        for dep in command.local_extra_deps:
            install_cmd.append(str(dep.absolute()))

    exec_command = CommandExec(command=shlex.join(install_cmd), env=command.env, prepend_paths=command.prepend_paths)
    execute_command_exec(exec_command)


def execute_command_python_env(command: CommandPythonEnv, *args: str) -> None:
    """Executes the command with the provided arguments using a cached Python environment."""
    # Get the environment cache path
    env_path = _get_app_runner_cache_path(command)
    python_executable = env_path / "bin" / "python"

    # Check if environment exists or if refresh is requested
    if not python_executable.exists() or command.refresh:
        _provision_environment(command)

    # Build command using the cached environment's Python interpreter
    command_args = shlex.split(command.command) + list(args)
    final_command = [str(python_executable)] + command_args

    exec_command = CommandExec(command=shlex.join(final_command), env=command.env, prepend_paths=command.prepend_paths)
    execute_command_exec(exec_command)
