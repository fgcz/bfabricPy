from pathlib import Path

import pytest
from inline_snapshot import snapshot

from bfabric_app_runner.commands.command_python_env import execute_command_python_env
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


@pytest.fixture
def mock_python_env_setup(mocker):
    """Common mocking setup for python environment tests."""
    # Mock the strategy classes instead of individual functions
    mock_cached_strategy = mocker.patch("bfabric_app_runner.commands.command_python_env.CachedEnvironmentStrategy")
    mock_ephemeral_strategy = mocker.patch(
        "bfabric_app_runner.commands.command_python_env.EphemeralEnvironmentStrategy"
    )

    # Create mock environment objects
    mock_env_path = Path("/cache/env/test_hash")
    mock_ephemeral_path = Path("/tmp/bfabric_app_runner_refresh_12345")

    # Mock environment for cached strategy
    mock_cached_env = mocker.MagicMock()
    mock_cached_env.python_executable = mock_env_path / "bin" / "python"
    mock_cached_env.bin_path = mock_env_path / "bin"
    mock_cached_strategy.return_value.get_environment.return_value = mock_cached_env

    # Mock environment for ephemeral strategy
    mock_ephemeral_env = mocker.MagicMock()
    mock_ephemeral_env.python_executable = mock_ephemeral_path / "bin" / "python"
    mock_ephemeral_env.bin_path = mock_ephemeral_path / "bin"
    mock_ephemeral_strategy.return_value.get_environment.return_value = mock_ephemeral_env

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    yield {
        "env_path": mock_env_path,
        "ephemeral_path": mock_ephemeral_path,
        "cached_strategy": mock_cached_strategy,
        "ephemeral_strategy": mock_ephemeral_strategy,
        "cached_env": mock_cached_env,
        "ephemeral_env": mock_ephemeral_env,
        "mock_execute": mock_execute,
    }


def test_execute_with_existing_environment(mock_python_env_setup):
    """Test execution when environment already exists."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_env_path = mock_python_env_setup["env_path"]

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd, "hello", "world")

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert str(mock_env_path / "bin" / "python") in called_command.command
    assert "script.py hello world" in called_command.command


def test_execute_with_refresh_flag(mock_python_env_setup):
    """Test execution with refresh flag uses ephemeral environment."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_ephemeral_path = mock_python_env_setup["ephemeral_path"]

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=True)
    execute_command_python_env(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()

    # Verify that the ephemeral path is used in the command
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert str(mock_ephemeral_path / "bin" / "python") in called_command.command
    assert "script.py" in called_command.command


def test_refresh_does_not_affect_cache(mock_python_env_setup):
    """Test that refresh operations don't affect the cached environment."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_exists = mock_python_env_setup["mock_exists"]

    # First, run with refresh=True (should use ephemeral path)
    cmd_refresh = CommandPythonEnv(
        pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=True
    )
    execute_command_python_env(cmd_refresh)

    # Reset mock for second call
    mock_execute.reset_mock()

    # Mock that cache doesn't exist (to trigger provisioning)
    mock_exists.return_value = False

    # Now run without refresh (should use cached path and provision normally)
    cmd_normal = CommandPythonEnv(
        pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=False
    )
    execute_command_python_env(cmd_normal)

    # Should still provision normally in cache path
    assert mock_execute.call_count == 3

    # Verify cache path is used, not ephemeral path
    cache_path = mock_python_env_setup["env_path"]
    ephemeral_path = mock_python_env_setup["ephemeral_path"]

    calls = mock_execute.call_args_list
    venv_call = calls[0][0][0]
    assert str(cache_path) in venv_call.command
    assert str(ephemeral_path) not in venv_call.command


def test_refresh_with_local_extra_deps(mock_python_env_setup):
    """Test refresh with local extra dependencies uses ephemeral environment."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_ephemeral_path = mock_python_env_setup["ephemeral_path"]

    cmd = CommandPythonEnv(
        pylock=Path("/test/pylock"),
        command="script.py",
        python_version="3.13",
        local_extra_deps=[Path("/test/wheel1.whl"), Path("/test/wheel2.whl")],
        refresh=True,
    )
    execute_command_python_env(cmd, "arg1")

    # Should call execute_command_exec 4 times: venv creation, pip install, local deps install, and execution
    assert mock_execute.call_count == 4

    # Verify all calls use ephemeral path
    calls = mock_execute.call_args_list

    # Check venv creation
    venv_call = calls[0][0][0]
    assert str(mock_ephemeral_path) in venv_call.command

    # Check pip install
    pip_call = calls[1][0][0]
    assert str(mock_ephemeral_path / "bin" / "python") in pip_call.command
    assert "--reinstall" in pip_call.command  # Should have --reinstall flag

    # Check local deps install
    deps_call = calls[2][0][0]
    assert str(mock_ephemeral_path / "bin" / "python") in deps_call.command
    assert "--no-deps" in deps_call.command
    assert "/test/wheel1.whl" in deps_call.command
    assert "/test/wheel2.whl" in deps_call.command

    # Check final execution
    exec_call = calls[3][0][0]
    assert str(mock_ephemeral_path / "bin" / "python") in exec_call.command
    assert "script.py arg1" in exec_call.command


def test_execute_with_missing_environment(mock_python_env_setup):
    """Test execution when environment doesn't exist yet."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_exists = mock_python_env_setup["mock_exists"]

    # Mock provisioned marker doesn't exist
    mock_exists.return_value = False

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Should call execute_command_exec 3 times: venv creation, pip install, and execution
    assert mock_execute.call_count == 3


def test_execute_with_local_extra_deps(mock_python_env_setup, mocker):
    """Test execution with local extra dependencies."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_exists = mock_python_env_setup["mock_exists"]

    # Mock provisioned marker doesn't exist (to trigger provisioning)
    mock_exists.return_value = False

    cmd = CommandPythonEnv(
        pylock=Path("/test/pylock"),
        command="script.py",
        python_version="3.13",
        local_extra_deps=[Path("/test/wheel1.whl"), Path("/test/wheel2.whl")],
    )
    execute_command_python_env(cmd, "arg1")

    # Check correct calls were made
    assert mock_execute.mock_calls == [
        mocker.call(CommandExec(command="uv venv -p 3.13 /cache/env/test_hash")),
        mocker.call(CommandExec(command="uv pip install -p /cache/env/test_hash/bin/python -r /test/pylock")),
        mocker.call(
            CommandExec(
                command="uv pip install -p /cache/env/test_hash/bin/python --no-deps /test/wheel1.whl /test/wheel2.whl"
            )
        ),
        mocker.call(
            CommandExec(
                command="/cache/env/test_hash/bin/python script.py arg1",
                prepend_paths=[Path("/cache/env/test_hash/bin")],
            )
        ),
    ]

    # Last call should be the execution
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert "script.py arg1" in called_command.command


def test_execute_with_env_and_prepend_paths(mock_python_env_setup):
    """Test execution with custom environment and prepend paths."""
    mock_execute = mock_python_env_setup["mock_execute"]

    cmd = CommandPythonEnv(
        pylock=Path("/test/pylock"),
        command="script.py",
        python_version="3.13",
        env={"CUSTOM_VAR": "value"},
        prepend_paths=[Path("/custom/bin")],
    )
    execute_command_python_env(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert called_command.env == {"CUSTOM_VAR": "value"}
    assert called_command.prepend_paths == [Path("/cache/env/test_hash/bin"), Path("/custom/bin")]


def test_hash(mocker):
    """Test that environment hash includes hostname."""
    from bfabric_app_runner.commands.command_python_env import _compute_env_hash

    # Mock resources
    mocker.patch("socket.gethostname", return_value="test-host")
    mock_path = mocker.MagicMock(spec=Path, name="mock_path")
    mock_path.absolute.return_value = Path("/test/pylock.toml")
    mock_path.stat.return_value.st_mtime = 1234567890

    cmd = CommandPythonEnv(pylock=mock_path, command="script.py", python_version="3.13")
    hash = _compute_env_hash(cmd)
    # This shouldn't change unless the implementation is changed.
    assert hash == snapshot("a4f31fefdd6f1312")


def test_file_locking_during_provisioning(mock_python_env_setup):
    """Test that file locking is used during environment provisioning."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_exists = mock_python_env_setup["mock_exists"]
    mock_flock = mock_python_env_setup["mock_flock"]

    # Mock provisioned marker doesn't exist (to trigger provisioning)
    mock_exists.return_value = False

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Verify lock was acquired
    mock_flock.assert_called_once()

    # Should call execute_command_exec for provisioning and execution
    assert mock_execute.call_count == 3  # venv, pip install, and final execution


def test_double_check_after_lock_acquisition(mock_python_env_setup):
    """Test that environment existence is checked again after acquiring lock."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_exists = mock_python_env_setup["mock_exists"]
    mock_flock = mock_python_env_setup["mock_flock"]

    # Mock provisioned marker exists (environment exists after lock acquired)
    # This simulates the case where another process created the environment
    # between when we might have checked initially and when we acquired the lock
    mock_exists.return_value = True

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Should acquire lock but skip provisioning since environment exists
    mock_flock.assert_called_once()
    # Should only call execute_command_exec once for the final execution (no provisioning)
    mock_execute.assert_called_once()


def test_refresh_does_not_use_locking(mock_python_env_setup):
    """Test that refresh operations don't use file locking since they use ephemeral environments."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_flock = mock_python_env_setup["mock_flock"]

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=True)
    execute_command_python_env(cmd)

    # Should NOT acquire lock for refresh operations
    mock_flock.assert_not_called()
    # Should call execute_command_exec 3 times for ephemeral environment provisioning
    assert mock_execute.call_count == 3
