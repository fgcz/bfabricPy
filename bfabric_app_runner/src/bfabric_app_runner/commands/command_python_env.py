import fcntl
import hashlib
import os
import shlex
import socket
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
    hostname = socket.gethostname()
    hash_input = f"{hostname}:{command.python_version or 'default'}:{command.pylock.absolute()}"
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

    # Install dependencies from pylock file (with dependency resolution)
    python_executable = env_path / "bin" / "python"
    install_cmd = ["uv", "pip", "install", "-p", str(python_executable), "-r", str(command.pylock)]

    if command.refresh:
        install_cmd.append("--reinstall")

    exec_command = CommandExec(command=shlex.join(install_cmd), env=command.env, prepend_paths=command.prepend_paths)
    execute_command_exec(exec_command)

    # Install local_extra_deps with --no-deps (no dependency resolution)
    if command.local_extra_deps:
        dep_install_cmd = ["uv", "pip", "install", "-p", str(python_executable), "--no-deps"]
        dep_install_cmd.extend(str(dep.absolute()) for dep in command.local_extra_deps)
        exec_command = CommandExec(
            command=shlex.join(dep_install_cmd), env=command.env, prepend_paths=command.prepend_paths
        )
        execute_command_exec(exec_command)

    # Mark environment as successfully provisioned
    provisioned_marker = env_path / ".provisioned"
    provisioned_marker.touch()


def execute_command_python_env(command: CommandPythonEnv, *args: str) -> None:
    """Executes the command with the provided arguments using a cached Python environment."""
    # Get the environment cache path
    env_path = _get_app_runner_cache_path(command)
    python_executable = env_path / "bin" / "python"
    provisioned_marker = env_path / ".provisioned"

    # Use file lock to prevent race conditions during provisioning
    lock_file = env_path.parent / f"{env_path.name}.lock"
    env_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_file.open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

        # Check if environment is properly provisioned or if refresh is requested (under lock)
        if not provisioned_marker.exists() or command.refresh:
            _provision_environment(command)

    # Build command using the cached environment's Python interpreter
    command_args = shlex.split(command.command) + list(args)
    final_command = [str(python_executable)] + command_args

    # Include venv's bin directory in prepend_paths
    venv_bin_path = env_path / "bin"
    prepend_paths = [venv_bin_path] + (command.prepend_paths or [])

    exec_command = CommandExec(command=shlex.join(final_command), env=command.env, prepend_paths=prepend_paths)
    execute_command_exec(exec_command)
