from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from bfabric_app_runner.commands.command_python_env import (
    PythonEnvironment,
    CachedEnvironmentStrategy,
    EphemeralEnvironmentStrategy,
    execute_command_python_env,
    _ensure_executable,
)
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


@pytest.fixture
def mock_uv(mocker):
    """Mock the uv binary path."""
    return mocker.patch("shutil.which", return_value="/usr/bin/uv")


@pytest.fixture
def mock_execute_command_exec(mocker):
    """Mock the execute_command_exec function."""
    return mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")


@pytest.fixture
def temp_env_path(tmp_path):
    """Provide a temporary environment path."""
    return tmp_path / "test_env"


@pytest.fixture
def sample_command():
    """Provide a sample CommandPythonEnv."""
    return CommandPythonEnv(
        pylock=Path("/test/requirements.txt"),
        command="my_script.py",
        python_version="3.13",
    )


class TestPythonEnvironment:
    """Tests for the PythonEnvironment class."""

    def test_init_sets_paths(self, temp_env_path, sample_command):
        """Test that initialization sets correct paths."""
        env = PythonEnvironment(temp_env_path, sample_command)

        assert env.env_path == temp_env_path
        assert env.command == sample_command
        assert env.python_executable == temp_env_path / "bin" / "python"
        assert env.bin_path == temp_env_path / "bin"

    def test_is_provisioned_when_marker_exists(self, temp_env_path, sample_command):
        """Test that is_provisioned returns True when marker file exists."""
        env = PythonEnvironment(temp_env_path, sample_command)
        marker = temp_env_path / ".provisioned"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()

        assert env.is_provisioned is True

    def test_is_provisioned_when_marker_missing(self, temp_env_path, sample_command):
        """Test that is_provisioned returns False when marker file is missing."""
        env = PythonEnvironment(temp_env_path, sample_command)

        assert env.is_provisioned is False

    def test_provision_workflow(self, temp_env_path, sample_command, mock_uv, mock_execute_command_exec):
        """Test that provision calls all necessary steps and creates marker."""
        # Create parent directory for marker file
        temp_env_path.mkdir(parents=True, exist_ok=True)

        env = PythonEnvironment(temp_env_path, sample_command)
        env.provision()

        # Should call execute_command_exec for venv creation and pip install
        assert mock_execute_command_exec.call_count == 2

        # Check venv creation command
        venv_call = mock_execute_command_exec.call_args_list[0][0][0]
        assert isinstance(venv_call, CommandExec)
        assert "uv venv -p 3.13" in venv_call.command
        assert str(temp_env_path) in venv_call.command

        # Check pip install command
        install_call = mock_execute_command_exec.call_args_list[1][0][0]
        assert "uv pip install" in install_call.command
        assert str(sample_command.pylock) in install_call.command

        # Check marker file created
        assert env.is_provisioned is True

    def test_provision_with_local_extra_deps(self, temp_env_path, mock_uv, mock_execute_command_exec):
        """Test that provision installs local extra dependencies."""
        temp_env_path.mkdir(parents=True, exist_ok=True)

        command = CommandPythonEnv(
            pylock=Path("/test/requirements.txt"),
            command="my_script.py",
            python_version="3.13",
            local_extra_deps=[Path("/test/wheel1.whl"), Path("/test/wheel2.whl")],
        )
        env = PythonEnvironment(temp_env_path, command)
        env.provision()

        # Should call execute_command_exec 3 times: venv, main deps, local deps
        assert mock_execute_command_exec.call_count == 3

        # Check local deps install command
        local_deps_call = mock_execute_command_exec.call_args_list[2][0][0]
        assert "uv pip install" in local_deps_call.command
        assert "--no-deps" in local_deps_call.command
        assert "/test/wheel1.whl" in local_deps_call.command
        assert "/test/wheel2.whl" in local_deps_call.command

    def test_provision_with_refresh_flag(self, temp_env_path, mock_uv, mock_execute_command_exec):
        """Test that provision with refresh uses --reinstall flag."""
        temp_env_path.mkdir(parents=True, exist_ok=True)

        command = CommandPythonEnv(
            pylock=Path("/test/requirements.txt"),
            command="my_script.py",
            python_version="3.13",
            refresh=True,
        )
        env = PythonEnvironment(temp_env_path, command)
        env.provision()

        # Check pip install command includes --reinstall
        install_call = mock_execute_command_exec.call_args_list[1][0][0]
        assert "--reinstall" in install_call.command

    def test_log_packages(self, temp_env_path, sample_command, mock_uv, mocker):
        """Test that log_packages runs pip list command."""
        mock_subprocess = mocker.patch("bfabric_app_runner.commands.command_python_env.subprocess.run")
        mock_subprocess.return_value = MagicMock(stdout="package1==1.0\npackage2==2.0\n")

        env = PythonEnvironment(temp_env_path, sample_command)
        env.log_packages()

        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "/usr/bin/uv"  # uv binary path
        assert "pip" in call_args
        assert "list" in call_args
        assert str(temp_env_path / "bin" / "python") in call_args


class TestCachedEnvironmentStrategy:
    """Tests for the CachedEnvironmentStrategy."""

    def test_get_environment_returns_python_environment(self, sample_command, mocker, tmp_path):
        """Test that get_environment returns a PythonEnvironment."""
        strategy = CachedEnvironmentStrategy()
        cache_path = tmp_path / "test_env"
        cache_path.mkdir(parents=True, exist_ok=True)

        # Create marker file to simulate already provisioned environment
        marker = cache_path / ".provisioned"
        marker.touch()

        mocker.patch.object(strategy, "_get_cache_path", return_value=cache_path)

        env = strategy.get_environment(sample_command)

        assert isinstance(env, PythonEnvironment)
        assert env.env_path == cache_path
        assert env.command == sample_command

    def test_provisions_when_not_provisioned(
        self, sample_command, mocker, mock_uv, mock_execute_command_exec, tmp_path
    ):
        """Test that get_environment provisions environment when not provisioned."""
        strategy = CachedEnvironmentStrategy()
        cache_path = tmp_path / "test_env"
        cache_path.mkdir(parents=True, exist_ok=True)

        mocker.patch.object(strategy, "_get_cache_path", return_value=cache_path)
        mock_log_packages = mocker.patch.object(PythonEnvironment, "log_packages")

        env = strategy.get_environment(sample_command)

        # Should have called provision (venv + pip install)
        assert mock_execute_command_exec.call_count == 2

        # Marker file should be created
        assert (cache_path / ".provisioned").exists()

        # log_packages should be called after provisioning
        mock_log_packages.assert_called_once()

    def test_does_not_log_packages_when_already_provisioned(self, sample_command, mocker, tmp_path):
        """Test that log_packages is not called when environment is already provisioned."""
        strategy = CachedEnvironmentStrategy()
        cache_path = tmp_path / "test_env"
        cache_path.mkdir(parents=True, exist_ok=True)

        # Create marker file to simulate already provisioned environment
        marker = cache_path / ".provisioned"
        marker.touch()

        mocker.patch.object(strategy, "_get_cache_path", return_value=cache_path)
        mock_log_packages = mocker.patch.object(PythonEnvironment, "log_packages")

        env = strategy.get_environment(sample_command)

        # log_packages should NOT be called since already provisioned
        mock_log_packages.assert_not_called()

    def test_compute_env_hash_includes_hostname(self, sample_command, mocker):
        """Test that environment hash includes hostname."""
        mocker.patch("socket.gethostname", return_value="test-host")
        mocker.patch("pathlib.Path.stat")

        strategy = CachedEnvironmentStrategy()
        hash1 = strategy._compute_env_hash(sample_command)

        # Change hostname and verify hash changes
        mocker.patch("socket.gethostname", return_value="other-host")
        hash2 = strategy._compute_env_hash(sample_command)

        assert hash1 != hash2

    def test_compute_env_hash_includes_python_version(self, mocker):
        """Test that environment hash includes Python version."""
        mocker.patch("socket.gethostname", return_value="test-host")
        mocker.patch("pathlib.Path.stat")

        strategy = CachedEnvironmentStrategy()

        cmd1 = CommandPythonEnv(pylock=Path("/test/req.txt"), command="script.py", python_version="3.12")
        cmd2 = CommandPythonEnv(pylock=Path("/test/req.txt"), command="script.py", python_version="3.13")

        hash1 = strategy._compute_env_hash(cmd1)
        hash2 = strategy._compute_env_hash(cmd2)

        assert hash1 != hash2

    def test_compute_env_hash_includes_pylock_mtime(self, mocker):
        """Test that environment hash includes pylock modification time."""
        mocker.patch("socket.gethostname", return_value="test-host")

        strategy = CachedEnvironmentStrategy()
        command = CommandPythonEnv(pylock=Path("/test/req.txt"), command="script.py", python_version="3.13")

        # Mock different mtimes
        mocker.patch("pathlib.Path.stat", return_value=MagicMock(st_mtime=1000))
        hash1 = strategy._compute_env_hash(command)

        mocker.patch("pathlib.Path.stat", return_value=MagicMock(st_mtime=2000))
        hash2 = strategy._compute_env_hash(command)

        assert hash1 != hash2

    def test_compute_env_hash_includes_local_deps(self, mocker):
        """Test that environment hash includes local extra dependencies."""
        mocker.patch("socket.gethostname", return_value="test-host")
        mocker.patch("pathlib.Path.stat")

        strategy = CachedEnvironmentStrategy()

        cmd1 = CommandPythonEnv(pylock=Path("/test/req.txt"), command="script.py", python_version="3.13")
        cmd2 = CommandPythonEnv(
            pylock=Path("/test/req.txt"),
            command="script.py",
            python_version="3.13",
            local_extra_deps=[Path("/test/wheel.whl")],
        )

        hash1 = strategy._compute_env_hash(cmd1)
        hash2 = strategy._compute_env_hash(cmd2)

        assert hash1 != hash2

    def test_get_cache_path_uses_xdg_cache_home(self, sample_command, mocker):
        """Test that cache path uses XDG_CACHE_HOME when set."""
        mocker.patch.dict("os.environ", {"XDG_CACHE_HOME": "/custom/cache"})
        mocker.patch("pathlib.Path.stat")
        mocker.patch("socket.gethostname", return_value="test-host")

        strategy = CachedEnvironmentStrategy()
        cache_path = strategy._get_cache_path(sample_command)

        assert str(cache_path).startswith("/custom/cache/bfabric_app_runner/envs/")

    def test_uses_file_locking(self, sample_command, mocker, mock_uv, mock_execute_command_exec, tmp_path):
        """Test that get_environment uses file locking."""
        strategy = CachedEnvironmentStrategy()
        cache_path = tmp_path / "test_env"
        cache_path.mkdir(parents=True, exist_ok=True)

        # Create marker to simulate already provisioned
        (cache_path / ".provisioned").touch()

        mocker.patch.object(strategy, "_get_cache_path", return_value=cache_path)
        mock_flock = mocker.patch("bfabric_app_runner.commands.command_python_env.fcntl.flock")

        strategy.get_environment(sample_command)

        # Verify flock was called
        mock_flock.assert_called_once()


class TestEphemeralEnvironmentStrategy:
    """Tests for the EphemeralEnvironmentStrategy."""

    def test_get_environment_returns_python_environment(
        self, sample_command, mocker, mock_uv, mock_execute_command_exec
    ):
        """Test that get_environment returns a PythonEnvironment with ephemeral path."""
        strategy = EphemeralEnvironmentStrategy()
        mocker.patch("tempfile.mkdtemp", return_value="/tmp/env_12345")
        mocker.patch("pathlib.Path.mkdir")
        mocker.patch("pathlib.Path.touch")
        mocker.patch.object(PythonEnvironment, "log_packages")

        env = strategy.get_environment(sample_command)

        assert isinstance(env, PythonEnvironment)
        assert env.env_path == Path("/tmp/env_12345")
        assert env.command == sample_command

    def test_always_provisions(self, sample_command, mocker, mock_uv, mock_execute_command_exec):
        """Test that ephemeral environments are always provisioned."""
        strategy = EphemeralEnvironmentStrategy()
        mocker.patch("tempfile.mkdtemp", return_value="/tmp/env_12345")
        mocker.patch("pathlib.Path.mkdir")
        mocker.patch("pathlib.Path.touch")
        mock_log_packages = mocker.patch.object(PythonEnvironment, "log_packages")

        strategy.get_environment(sample_command)

        # Should have called provision (venv + pip install)
        assert mock_execute_command_exec.call_count == 2

        # log_packages should be called after provisioning
        mock_log_packages.assert_called_once()

    def test_uses_cache_directory_for_temp(self, sample_command, mocker, mock_uv, mock_execute_command_exec):
        """Test that ephemeral environments are created in cache directory."""
        strategy = EphemeralEnvironmentStrategy()
        mock_mkdtemp = mocker.patch("tempfile.mkdtemp", return_value="/tmp/env_12345")
        mocker.patch("pathlib.Path.mkdir")
        mocker.patch("pathlib.Path.touch")
        mocker.patch.object(PythonEnvironment, "log_packages")

        strategy.get_environment(sample_command)

        # Check that mkdtemp was called with cache directory
        call_kwargs = mock_mkdtemp.call_args[1]
        assert "bfabric_app_runner/ephemeral" in str(call_kwargs["dir"])


class TestExecuteCommandPythonEnv:
    """Tests for the execute_command_python_env function."""

    @pytest.fixture
    def mock_ensure_environment(self, mocker):
        """Mock _ensure_environment to return a test path."""
        return mocker.patch(
            "bfabric_app_runner.commands.command_python_env._ensure_environment",
            return_value=Path("/test/env"),
        )

    @pytest.fixture
    def mock_cleanup(self, mocker):
        """Mock cleanup function."""
        return mocker.patch("bfabric_app_runner.commands.command_python_env._cleanup_ephemeral_environment")

    def test_executes_with_cached_environment(self, sample_command, mock_ensure_environment, mock_execute_command_exec):
        """Test execution uses cached environment by default."""
        execute_command_python_env(sample_command)

        mock_ensure_environment.assert_called_once_with(sample_command)
        mock_execute_command_exec.assert_called_once()

    def test_executes_with_ephemeral_environment(
        self, mock_ensure_environment, mock_execute_command_exec, mock_cleanup
    ):
        """Test execution with refresh flag uses ephemeral environment and cleans up."""
        command = CommandPythonEnv(
            pylock=Path("/test/req.txt"),
            command="script.py",
            python_version="3.13",
            refresh=True,
        )

        execute_command_python_env(command)

        mock_ensure_environment.assert_called_once_with(command)
        mock_execute_command_exec.assert_called_once()
        mock_cleanup.assert_called_once_with(Path("/test/env"))

    def test_no_cleanup_for_cached_environment(
        self, sample_command, mock_ensure_environment, mock_execute_command_exec, mock_cleanup
    ):
        """Test that cached environments are not cleaned up."""
        execute_command_python_env(sample_command)

        mock_cleanup.assert_not_called()

    def test_passes_arguments_to_command(self, sample_command, mock_ensure_environment, mock_execute_command_exec):
        """Test that additional arguments are passed to the command."""
        execute_command_python_env(sample_command, "arg1", "arg2", "arg3")

        call_args = mock_execute_command_exec.call_args[0][0]
        assert "arg1" in call_args.command
        assert "arg2" in call_args.command
        assert "arg3" in call_args.command

    def test_includes_venv_bin_in_prepend_paths(
        self, sample_command, mock_ensure_environment, mock_execute_command_exec
    ):
        """Test that venv bin directory is prepended to PATH."""
        execute_command_python_env(sample_command)

        call_args = mock_execute_command_exec.call_args[0][0]
        assert Path("/test/env/bin") in call_args.prepend_paths

    def test_preserves_custom_prepend_paths(self, mock_ensure_environment, mock_execute_command_exec):
        """Test that custom prepend paths are preserved and venv bin is prepended."""
        command = CommandPythonEnv(
            pylock=Path("/test/req.txt"),
            command="script.py",
            python_version="3.13",
            prepend_paths=[Path("/custom/bin1"), Path("/custom/bin2")],
        )

        execute_command_python_env(command)

        call_args = mock_execute_command_exec.call_args[0][0]
        assert call_args.prepend_paths == [Path("/test/env/bin"), Path("/custom/bin1"), Path("/custom/bin2")]

    def test_passes_environment_variables(self, mock_ensure_environment, mock_execute_command_exec):
        """Test that environment variables are passed through."""
        command = CommandPythonEnv(
            pylock=Path("/test/req.txt"),
            command="script.py",
            python_version="3.13",
            env={"VAR1": "value1", "VAR2": "value2"},
        )

        execute_command_python_env(command)

        call_args = mock_execute_command_exec.call_args[0][0]
        assert call_args.env == {"VAR1": "value1", "VAR2": "value2"}

    def test_cleanup_on_exception_with_refresh(self, mock_ensure_environment, mock_execute_command_exec, mock_cleanup):
        """Test that ephemeral environment is cleaned up even on exception."""
        command = CommandPythonEnv(
            pylock=Path("/test/req.txt"),
            command="script.py",
            python_version="3.13",
            refresh=True,
        )
        mock_execute_command_exec.side_effect = RuntimeError("Execution failed")

        with pytest.raises(RuntimeError):
            execute_command_python_env(command)

        # Cleanup should still be called
        mock_cleanup.assert_called_once_with(Path("/test/env"))


class TestEnsureExecutable:
    """Tests for the _ensure_executable function."""

    def test_uses_bin_script_when_exists(self, mocker):
        """Test that _ensure_executable uses script from bin directory when it exists."""
        env_path = Path("/test/env")

        def mock_exists(self):
            return str(self) == "/test/env/bin/my-script"

        mocker.patch("pathlib.Path.exists", mock_exists)

        result = _ensure_executable(["my-script", "arg1", "arg2"], env_path)

        assert result == ["/test/env/bin/my-script", "arg1", "arg2"]

    def test_falls_back_to_python_when_script_missing(self, mocker):
        """Test that _ensure_executable falls back to python interpreter."""
        env_path = Path("/test/env")
        mocker.patch("pathlib.Path.exists", return_value=False)

        result = _ensure_executable(["my-script.py", "arg1", "arg2"], env_path)

        assert result == ["/test/env/bin/python", "my-script.py", "arg1", "arg2"]

    def test_handles_script_with_no_args(self, mocker):
        """Test that _ensure_executable handles script with no arguments."""
        env_path = Path("/test/env")
        mocker.patch("pathlib.Path.exists", return_value=True)

        result = _ensure_executable(["my-script"], env_path)

        assert result == ["/test/env/bin/my-script"]
