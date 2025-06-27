from pathlib import Path
import pytest
from inline_snapshot import snapshot
from bfabric_app_runner.commands.command_python_env import execute_command_python_env
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


@pytest.fixture
def mock_python_env_setup(mocker):
    """Common mocking setup for python environment tests."""
    # Mock the cache path
    mock_get_cache_path = mocker.patch("bfabric_app_runner.commands.command_python_env._get_app_runner_cache_path")
    mock_env_path = Path("/cache/env/test_hash")
    mock_get_cache_path.return_value = mock_env_path

    # Mock filesystem operations
    mock_exists = mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch.object(Path, "mkdir")
    mocker.patch.object(Path, "touch")  # Mock the touch method for .provisioned marker

    # Mock file operations - use Path.open since that's what the code uses
    mocker.patch.object(Path, "open", mocker.mock_open())
    mock_flock = mocker.patch("fcntl.flock")

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    yield {
        "env_path": mock_env_path,
        "mock_exists": mock_exists,
        "mock_flock": mock_flock,
        "mock_execute": mock_execute,
    }


def test_execute_with_existing_environment(mock_python_env_setup):
    """Test execution when environment already exists."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_env_path = mock_python_env_setup["env_path"]

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd, "hello", "world")

    # Should call execute_command_exec once for execution (no provisioning needed)
    mock_execute.assert_called_once()
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert str(mock_env_path / "bin" / "python") in called_command.command
    assert "script.py hello world" in called_command.command


def test_execute_with_refresh_flag(mock_python_env_setup):
    """Test execution with refresh flag forces re-provisioning."""
    mock_execute = mock_python_env_setup["mock_execute"]

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=True)
    execute_command_python_env(cmd)

    # Should call execute_command_exec 3 times: venv creation, pip install, and execution
    assert mock_execute.call_count == 3


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
        mocker.call(snapshot(CommandExec(command="uv venv -p 3.13 /cache/env/test_hash"))),
        mocker.call(snapshot(CommandExec(command="uv pip install -p /cache/env/test_hash/bin/python -r /test/pylock"))),
        mocker.call(
            snapshot(
                CommandExec(
                    command="uv pip install -p /cache/env/test_hash/bin/python --no-deps /test/wheel1.whl /test/wheel2.whl"
                )
            )
        ),
        mocker.call(
            snapshot(
                CommandExec(
                    command="/cache/env/test_hash/bin/python script.py arg1",
                    prepend_paths=[Path("/cache/env/test_hash/bin")],
                )
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


def test_hash_includes_hostname(mocker):
    """Test that environment hash includes hostname."""
    from bfabric_app_runner.commands.command_python_env import _compute_env_hash

    # Mock hostname
    mock_hostname = mocker.patch("socket.gethostname", return_value="test-host")

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    hash1 = _compute_env_hash(cmd)

    # Change hostname and verify hash changes
    mock_hostname.return_value = "different-host"
    hash2 = _compute_env_hash(cmd)

    assert hash1 != hash2


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
