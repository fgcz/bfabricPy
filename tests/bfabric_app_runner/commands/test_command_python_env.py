from pathlib import Path
from inline_snapshot import snapshot
from bfabric_app_runner.commands.command_python_env import execute_command_python_env
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


def test_execute_with_existing_environment(mocker):
    """Test execution when environment already exists."""
    # Mock the cache path and python executable existence
    mock_get_cache_path = mocker.patch("bfabric_app_runner.commands.command_python_env._get_app_runner_cache_path")
    mock_env_path = Path("/cache/env/test_hash")
    mock_get_cache_path.return_value = mock_env_path

    # Mock python executable exists
    mocker.patch.object(Path, "exists", return_value=True)
    # Mock mkdir to prevent filesystem operations
    mocker.patch.object(Path, "mkdir")
    # Mock file operations
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("fcntl.flock")

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd, "hello", "world")

    # Should call execute_command_exec once for execution (no provisioning needed)
    mock_execute.assert_called_once()
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert str(mock_env_path / "bin" / "python") in called_command.command
    assert "script.py hello world" in called_command.command


def test_execute_with_refresh_flag(mocker):
    """Test execution with refresh flag forces re-provisioning."""
    # Mock the cache path
    mock_get_cache_path = mocker.patch("bfabric_app_runner.commands.command_python_env._get_app_runner_cache_path")
    mock_env_path = Path("/cache/env/test_hash")
    mock_get_cache_path.return_value = mock_env_path

    # Mock python executable exists but refresh should still cause re-provisioning
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch.object(Path, "mkdir")
    # Mock file operations
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("fcntl.flock")

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=True)
    execute_command_python_env(cmd)

    # Should call execute_command_exec 3 times: venv creation, pip install, and execution
    assert mock_execute.call_count == 3


def test_execute_with_missing_environment(mocker):
    """Test execution when environment doesn't exist yet."""
    # Mock the cache path
    mock_get_cache_path = mocker.patch("bfabric_app_runner.commands.command_python_env._get_app_runner_cache_path")
    mock_env_path = Path("/cache/env/test_hash")
    mock_get_cache_path.return_value = mock_env_path

    # Mock python executable doesn't exist
    mocker.patch.object(Path, "exists", return_value=False)
    mocker.patch.object(Path, "mkdir")
    # Mock file operations
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("fcntl.flock")

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Should call execute_command_exec 3 times: venv creation, pip install, and execution
    assert mock_execute.call_count == 3


def test_execute_with_local_extra_deps(mocker):
    """Test execution with local extra dependencies."""
    # Mock the cache path
    mock_get_cache_path = mocker.patch("bfabric_app_runner.commands.command_python_env._get_app_runner_cache_path")
    mock_env_path = Path("/cache/env/test_hash")
    mock_get_cache_path.return_value = mock_env_path

    # Mock python executable doesn't exist (to trigger provisioning)
    mocker.patch.object(Path, "exists", return_value=False)
    mocker.patch.object(Path, "mkdir")
    # Mock file operations
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("fcntl.flock")

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

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
        mocker.call(snapshot(CommandExec(command="/cache/env/test_hash/bin/python script.py arg1"))),
    ]

    # Last call should be the execution
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert "script.py arg1" in called_command.command


def test_execute_with_env_and_prepend_paths(mocker):
    """Test execution with custom environment and prepend paths."""
    # Mock the cache path
    mock_get_cache_path = mocker.patch("bfabric_app_runner.commands.command_python_env._get_app_runner_cache_path")
    mock_env_path = Path("/cache/env/test_hash")
    mock_get_cache_path.return_value = mock_env_path

    # Mock python executable exists
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch.object(Path, "mkdir")
    # Mock file operations
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("fcntl.flock")

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

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
    assert called_command.prepend_paths == [Path("/custom/bin")]


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


def test_file_locking_during_provisioning(mocker):
    """Test that file locking is used during environment provisioning."""
    # Mock the cache path
    mock_get_cache_path = mocker.patch("bfabric_app_runner.commands.command_python_env._get_app_runner_cache_path")
    mock_env_path = Path("/cache/env/test_hash")
    mock_get_cache_path.return_value = mock_env_path

    # Mock python executable doesn't exist (to trigger provisioning)
    mocker.patch.object(Path, "exists", return_value=False)
    mocker.patch.object(Path, "mkdir")

    # Mock file operations and fcntl.flock
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_flock = mocker.patch("fcntl.flock")
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Verify lock file was opened and locked
    mock_open.assert_any_call(mock_env_path.parent / f"{mock_env_path.name}.lock", "a")
    mock_flock.assert_called_once()

    # Should call execute_command_exec for provisioning and execution
    assert mock_execute.call_count == 3  # venv, pip install, and final execution


def test_double_check_after_lock_acquisition(mocker):
    """Test that environment existence is checked again after acquiring lock."""
    # Mock the cache path
    mock_get_cache_path = mocker.patch("bfabric_app_runner.commands.command_python_env._get_app_runner_cache_path")
    mock_env_path = Path("/cache/env/test_hash")
    mock_get_cache_path.return_value = mock_env_path

    # Mock Path.exists to return False first (to trigger provisioning), then True (after lock acquired)
    mock_exists = mocker.patch.object(Path, "exists")
    # Provide enough values: first check fails, second check (after lock) succeeds, plus any additional calls
    mock_exists.side_effect = [False, True, True, True, True]  # Extra True values for any additional calls

    mocker.patch.object(Path, "mkdir")
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_flock = mocker.patch("fcntl.flock")
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Should acquire lock but skip provisioning since environment exists after lock
    mock_flock.assert_called_once()
    # Should only call execute_command_exec once for the final execution (no provisioning)
    mock_execute.assert_called_once()
