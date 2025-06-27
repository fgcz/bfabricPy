from pathlib import Path

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

    # Mock python executable exists
    mocker.patch.object(Path, "exists", return_value=True)

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    cmd = CommandPythonEnv(
        pylock=Path("/test/pylock"),
        command="script.py",
        python_version="3.13",
        local_extra_deps=[Path("/test/wheel1.whl"), Path("/test/wheel2.whl")],
    )
    execute_command_python_env(cmd, "arg1")

    # Should call execute_command_exec once for execution (environment exists)
    mock_execute.assert_called_once()
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
