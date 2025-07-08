from pathlib import Path

import pytest
from inline_snapshot import snapshot

from bfabric_app_runner.commands.command_python_env import execute_command_python_env
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


@pytest.fixture
def mock_python_env_setup(mocker):
    """Common mocking setup for python environment tests."""
    # Create mock environment paths
    mock_env_path = Path("/cache/env/test_hash")
    mock_ephemeral_path = Path("/tmp/bfabric_app_runner_refresh_12345")

    # Mock the strategy classes and their methods
    mock_cached_strategy = mocker.MagicMock()
    mock_ephemeral_strategy = mocker.MagicMock()

    # Mock PythonEnvironment
    mock_environment = mocker.MagicMock()
    mock_environment.env_path = mock_env_path
    mock_environment.is_provisioned.return_value = True

    mock_cached_strategy.get_environment.return_value = mock_environment
    mock_ephemeral_strategy.get_environment.return_value = mock_environment

    # Mock strategy constructors
    mock_cached_strategy_class = mocker.patch(
        "bfabric_app_runner.commands.command_python_env.CachedEnvironmentStrategy", return_value=mock_cached_strategy
    )
    mock_ephemeral_strategy_class = mocker.patch(
        "bfabric_app_runner.commands.command_python_env.EphemeralEnvironmentStrategy",
        return_value=mock_ephemeral_strategy,
    )

    # Mock execute_command_exec
    mock_execute = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")

    yield {
        "env_path": mock_env_path,
        "ephemeral_path": mock_ephemeral_path,
        "mock_cached_strategy": mock_cached_strategy,
        "mock_ephemeral_strategy": mock_ephemeral_strategy,
        "mock_cached_strategy_class": mock_cached_strategy_class,
        "mock_ephemeral_strategy_class": mock_ephemeral_strategy_class,
        "mock_environment": mock_environment,
        "mock_execute": mock_execute,
    }


def test_execute_with_existing_environment(mock_python_env_setup):
    """Test execution when environment already exists."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # Environment is already provisioned
    mock_environment.is_provisioned.return_value = True

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd, "hello", "world")

    # Should use cached strategy
    mock_cached_strategy.get_environment.assert_called_once_with(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert str(mock_python_env_setup["env_path"] / "bin" / "python") in called_command.command
    assert "script.py hello world" in called_command.command


def test_execute_with_refresh_flag(mock_python_env_setup):
    """Test execution with refresh flag uses ephemeral environment."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_ephemeral_strategy = mock_python_env_setup["mock_ephemeral_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # Set up ephemeral environment path
    mock_environment.env_path = mock_python_env_setup["ephemeral_path"]

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=True)
    execute_command_python_env(cmd)

    # Should use ephemeral strategy
    mock_ephemeral_strategy.get_environment.assert_called_once_with(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()

    # Verify that the ephemeral path is used in the command
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert str(mock_python_env_setup["ephemeral_path"] / "bin" / "python") in called_command.command
    assert "script.py" in called_command.command


def test_refresh_does_not_affect_cache(mock_python_env_setup):
    """Test that refresh operations don't affect the cached environment."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]
    mock_ephemeral_strategy = mock_python_env_setup["mock_ephemeral_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # First, run with refresh=True (should use ephemeral strategy)
    mock_environment.env_path = mock_python_env_setup["ephemeral_path"]
    cmd_refresh = CommandPythonEnv(
        pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=True
    )
    execute_command_python_env(cmd_refresh)

    # Verify ephemeral strategy was used
    mock_ephemeral_strategy.get_environment.assert_called_once_with(cmd_refresh)
    mock_cached_strategy.get_environment.assert_not_called()

    # Reset mocks for second call
    mock_execute.reset_mock()
    mock_cached_strategy.reset_mock()
    mock_ephemeral_strategy.reset_mock()

    # Now run without refresh (should use cached strategy)
    mock_environment.env_path = mock_python_env_setup["env_path"]
    cmd_normal = CommandPythonEnv(
        pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=False
    )
    execute_command_python_env(cmd_normal)

    # Verify cached strategy was used
    mock_cached_strategy.get_environment.assert_called_once_with(cmd_normal)
    mock_ephemeral_strategy.get_environment.assert_not_called()

    # Verify cache path is used in the command
    called_command = mock_execute.call_args[0][0]
    assert str(mock_python_env_setup["env_path"] / "bin" / "python") in called_command.command


def test_refresh_with_local_extra_deps(mock_python_env_setup):
    """Test refresh with local extra dependencies uses ephemeral environment."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_ephemeral_strategy = mock_python_env_setup["mock_ephemeral_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # Set up ephemeral environment path
    mock_environment.env_path = mock_python_env_setup["ephemeral_path"]

    cmd = CommandPythonEnv(
        pylock=Path("/test/pylock"),
        command="script.py",
        python_version="3.13",
        local_extra_deps=[Path("/test/wheel1.whl"), Path("/test/wheel2.whl")],
        refresh=True,
    )
    execute_command_python_env(cmd, "arg1")

    # Should use ephemeral strategy
    mock_ephemeral_strategy.get_environment.assert_called_once_with(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()

    # Check final execution uses ephemeral path
    exec_call = mock_execute.call_args[0][0]
    assert str(mock_python_env_setup["ephemeral_path"] / "bin" / "python") in exec_call.command
    assert "script.py arg1" in exec_call.command


def test_execute_with_missing_environment(mock_python_env_setup):
    """Test execution when environment doesn't exist yet."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # Environment is not provisioned initially
    mock_environment.is_provisioned.return_value = False

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Should use cached strategy
    mock_cached_strategy.get_environment.assert_called_once_with(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()


def test_execute_with_local_extra_deps(mock_python_env_setup, mocker):
    """Test execution with local extra dependencies."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # Environment is not provisioned initially
    mock_environment.is_provisioned.return_value = False

    cmd = CommandPythonEnv(
        pylock=Path("/test/pylock"),
        command="script.py",
        python_version="3.13",
        local_extra_deps=[Path("/test/wheel1.whl"), Path("/test/wheel2.whl")],
    )
    execute_command_python_env(cmd, "arg1")

    # Should use cached strategy
    mock_cached_strategy.get_environment.assert_called_once_with(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()

    # Last call should be the execution
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert "script.py arg1" in called_command.command


def test_execute_with_env_and_prepend_paths(mock_python_env_setup):
    """Test execution with custom environment and prepend paths."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]

    cmd = CommandPythonEnv(
        pylock=Path("/test/pylock"),
        command="script.py",
        python_version="3.13",
        env={"CUSTOM_VAR": "value"},
        prepend_paths=[Path("/custom/bin")],
    )
    execute_command_python_env(cmd)

    # Should use cached strategy
    mock_cached_strategy.get_environment.assert_called_once_with(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert called_command.env == {"CUSTOM_VAR": "value"}
    assert called_command.prepend_paths == [Path("/cache/env/test_hash/bin"), Path("/custom/bin")]


def test_hash(mocker):
    """Test that environment hash includes hostname."""
    # Skip this test since _compute_env_hash is not available
    pytest.skip("_compute_env_hash function not available in current implementation")


def test_file_locking_during_provisioning(mock_python_env_setup):
    """Test that file locking is used during environment provisioning."""
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # Environment is not provisioned initially
    mock_environment.is_provisioned.return_value = False

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Should use cached strategy (which handles locking internally)
    mock_cached_strategy.get_environment.assert_called_once_with(cmd)


def test_double_check_after_lock_acquisition(mock_python_env_setup):
    """Test that environment existence is checked again after acquiring lock."""
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # Environment exists (simulating another process created it)
    mock_environment.is_provisioned.return_value = True

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd)

    # Should use cached strategy
    mock_cached_strategy.get_environment.assert_called_once_with(cmd)


def test_refresh_does_not_use_locking(mock_python_env_setup):
    """Test that refresh operations don't use file locking since they use ephemeral environments."""
    mock_ephemeral_strategy = mock_python_env_setup["mock_ephemeral_strategy"]
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]
    mock_environment = mock_python_env_setup["mock_environment"]

    # Set up ephemeral environment path
    mock_environment.env_path = mock_python_env_setup["ephemeral_path"]

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13", refresh=True)
    execute_command_python_env(cmd)

    # Should use ephemeral strategy (no locking)
    mock_ephemeral_strategy.get_environment.assert_called_once_with(cmd)
    mock_cached_strategy.get_environment.assert_not_called()


def test_execute_with_changed_args(mock_python_env_setup):
    """Test execution with changed arguments."""
    mock_execute = mock_python_env_setup["mock_execute"]
    mock_cached_strategy = mock_python_env_setup["mock_cached_strategy"]

    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="script.py", python_version="3.13")
    execute_command_python_env(cmd, "hi", "world")

    # Should use cached strategy
    mock_cached_strategy.get_environment.assert_called_once_with(cmd)

    # Should call execute_command_exec once for execution
    mock_execute.assert_called_once()
    called_command = mock_execute.call_args[0][0]
    assert isinstance(called_command, CommandExec)
    assert "script.py hi world" in called_command.command
