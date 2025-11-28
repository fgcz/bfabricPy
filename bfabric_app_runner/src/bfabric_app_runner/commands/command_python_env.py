import fcntl
import hashlib
import os
import shlex
import shutil
import socket
import subprocess
import tempfile
from functools import cached_property
from pathlib import Path
from typing import Protocol, Annotated

import cyclopts
from loguru import logger

from bfabric_app_runner.commands.command_exec import execute_command_exec
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


class PythonEnvironment:
    """Represents a Python virtual environment with provisioning and execution capabilities."""

    def __init__(self, env_path: Path, command: CommandPythonEnv) -> None:
        self.env_path = env_path
        self.command = command
        self.python_executable = env_path / "bin" / "python"
        self.bin_path = env_path / "bin"

    def provision(self) -> None:
        """Provision the Python environment."""
        self._create_virtual_environment()
        self._install_dependencies()
        self._install_local_deps()
        self._mark_provisioned()

    @property
    def is_provisioned(self) -> bool:
        """True if the environment is already provisioned."""
        return self._provisioned_marker.exists()

    def log_packages(self, level: str = "DEBUG") -> None:
        """Log installed packages in the environment for debugging."""
        list_cmd = [self._uv_bin, "pip", "list", "-p", str(self.python_executable)]
        proc = subprocess.run(list_cmd, check=False, capture_output=True, text=True)
        logger.log(level, f"Installed packages in {self.env_path}:\n{proc.stdout}")

    @cached_property
    def _uv_bin(self) -> str:
        return shutil.which("uv")

    def _create_virtual_environment(self) -> None:
        """Create a virtual environment using uv venv."""
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        venv_cmd = [self._uv_bin, "venv", "-p", self.command.python_version, str(self.env_path)]
        self._execute_shell_cmd(venv_cmd)

    def _install_dependencies(self) -> None:
        """Install dependencies from pylock file."""
        install_cmd = [
            self._uv_bin,
            "pip",
            "install",
            "-p",
            str(self.python_executable),
            "-r",
            str(self.command.pylock),
        ]
        if self.command.refresh:
            install_cmd.append("--reinstall")
        self._execute_shell_cmd(install_cmd)

    def _install_local_deps(self) -> None:
        """Install local extra dependencies with --no-deps."""
        if not self.command.local_extra_deps:
            return

        dep_install_cmd = [self._uv_bin, "pip", "install", "-p", str(self.python_executable), "--no-deps"]
        dep_install_cmd.extend(str(dep.absolute()) for dep in self.command.local_extra_deps)
        self._execute_shell_cmd(dep_install_cmd)

    def _execute_shell_cmd(self, dep_install_cmd: list[str]) -> None:
        exec_command = CommandExec(
            command=shlex.join(dep_install_cmd), env=self.command.env, prepend_paths=self.command.prepend_paths
        )
        execute_command_exec(exec_command)

    def _mark_provisioned(self) -> None:
        """Mark environment as successfully provisioned."""
        self._provisioned_marker.touch()

    @property
    def _provisioned_marker(self) -> Path:
        """Path to the provisioned marker file."""
        return self.env_path / ".provisioned"


class EnvironmentStrategy(Protocol):
    """Protocol for obtaining Python environments."""

    def get_environment(self, command: CommandPythonEnv) -> PythonEnvironment:
        """Get a Python environment for the given command."""
        ...


class CachedEnvironmentStrategy:
    """Strategy for cached environments with file locking."""

    def get_environment(self, command: CommandPythonEnv) -> PythonEnvironment:
        env_path = self._get_cache_path(command)
        environment = PythonEnvironment(env_path, command)

        # Use file lock to prevent race conditions during provisioning
        lock_file = env_path.parent / f"{env_path.name}.lock"
        env_path.parent.mkdir(parents=True, exist_ok=True)

        with lock_file.open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

            # Check if environment is properly provisioned (under lock)
            if not environment.is_provisioned:
                logger.info(f"Provisioning Python environment at {env_path}")
                environment.provision()
                environment.log_packages()

        return environment

    def _get_cache_path(self, command: CommandPythonEnv) -> Path:
        """Get the app_runner cache directory for Python environments."""
        cache_dir = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser()
        app_runner_cache = cache_dir / "bfabric_app_runner" / "envs"
        env_hash = self._compute_env_hash(command)
        return app_runner_cache / env_hash

    def _compute_env_hash(self, command: CommandPythonEnv) -> str:
        """Returns a hash for the environment based on the command's specifications."""
        hostname = socket.gethostname()
        hash_input = f"{hostname}:{command.python_version}:{command.pylock.absolute()}:{command.pylock.stat().st_mtime}"
        if command.local_extra_deps:
            deps_str = ",".join(str(p.absolute()) for p in command.local_extra_deps)
            hash_input += f":{deps_str}"
        env_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        logger.debug(f"Environment hash for input: {hash_input!r} is {env_hash!r}")
        return env_hash


class EphemeralEnvironmentStrategy:
    """Strategy for ephemeral (temporary) environments."""

    def get_environment(self, command: CommandPythonEnv) -> PythonEnvironment:
        env_path = self._get_ephemeral_path()
        environment = PythonEnvironment(env_path, command)

        logger.info(f"Provisioning ephemeral Python environment at {env_path} (refresh mode)")
        environment.provision()
        environment.log_packages()
        return environment

    def _get_ephemeral_path(self) -> Path:
        """Get an ephemeral directory for ephemeral (refresh) environments using cache directory."""
        # Use the same cache directory as cached environments
        cache_dir = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser()
        app_runner_cache = cache_dir / "bfabric_app_runner" / "ephemeral"

        # Create a unique temporary subdirectory within the cache
        app_runner_cache.mkdir(parents=True, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="env_", dir=app_runner_cache)
        return Path(temp_dir)


def _ensure_environment(command: CommandPythonEnv) -> Path:
    """Ensure the Python environment exists and return its path."""
    strategy = EphemeralEnvironmentStrategy() if command.refresh else CachedEnvironmentStrategy()
    environment = strategy.get_environment(command)
    return environment.env_path


def execute_command_python_env(command: Annotated[CommandPythonEnv, cyclopts.Parameter(name="*")], *args: str) -> None:
    """Executes the command with the provided arguments using a Python environment."""
    # Ensure the environment exists (either cached or ephemeral)
    env_path = _ensure_environment(command)

    try:
        # Build command using the environment's Python interpreter
        command_args = shlex.split(command.command) + list(args)
        final_command = _ensure_executable(command_args, env_path)

        # Include venv's bin directory in prepend_paths
        venv_bin_path = env_path / "bin"
        prepend_paths = [venv_bin_path] + (command.prepend_paths or [])

        exec_command = CommandExec(command=shlex.join(final_command), env=command.env, prepend_paths=prepend_paths)
        execute_command_exec(exec_command)
    finally:
        # Clean up ephemeral environments after use
        if command.refresh:
            _cleanup_ephemeral_environment(env_path)


def _ensure_executable(command_args: list[str], env_path: Path) -> list[str]:
    candidate_script = env_path / "bin" / command_args[0]
    logger.info("Checking if candidate script exists: {}", candidate_script)
    if candidate_script.exists():
        logger.info("Found candidate script: {}", candidate_script)
        return [str(candidate_script), *command_args[1:]]

    # Fallback to using the Python interpreter directly
    logger.info("Falling back to using Python interpreter at {}", env_path / "bin" / "python")
    python_executable = env_path / "bin" / "python"
    return [str(python_executable), *command_args]


def _cleanup_ephemeral_environment(env_path: Path) -> None:
    """Clean up ephemeral environment after use."""
    try:
        if env_path.exists():
            logger.info(f"Cleaning up ephemeral environment at {env_path}")
            shutil.rmtree(env_path)
    except (OSError, PermissionError) as e:
        logger.warning(f"Failed to cleanup ephemeral environment at {env_path}: {e}")


app = cyclopts.App()
app.command(execute_command_python_env, name="execute")

if __name__ == "__main__":
    app()
