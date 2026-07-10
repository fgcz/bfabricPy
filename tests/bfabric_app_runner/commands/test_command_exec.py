import subprocess
from pathlib import Path

import pytest

from bfabric_app_runner.commands.command_exec import execute_command_exec
from bfabric_app_runner.specs.app.commands_spec import CommandExec


@pytest.fixture
def command_minimal():
    return CommandExec(command="echo 'hello world'")


@pytest.fixture
def command_full():
    return CommandExec(
        command='bash -c \'echo "hello $NAME" && echo "$PATH"\'',
        env={"NAME": "sun"},
        prepend_paths=[Path("/usr/local/bin"), Path("~/bin")],
    )


@pytest.fixture
def subprocess_run(mocker):
    return mocker.patch("subprocess.run")


def test_execute_minimal(command_minimal, subprocess_run):
    execute_command_exec(command_minimal, "hello", "world", environ={"NAME": "testing"})
    subprocess_run.assert_called_once_with(
        ["echo", "hello world", "hello", "world"],
        env={"NAME": "testing"},
        check=True,
    )


def test_execute_full(mocker, command_full, subprocess_run):
    mocker.patch.dict("os.environ", {"HOME": "/home/user"})
    execute_command_exec(command_full, "hello", "world", environ={"NAME": "testing"})
    subprocess_run.assert_called_once_with(
        [
            "bash",
            "-c",
            'echo "hello $NAME" && echo "$PATH"',
            "hello",
            "world",
        ],
        check=True,
        env={"NAME": "sun", "PATH": "/usr/local/bin:/home/user/bin:"},
    )


def test_execute_captures_and_logs_output_at_level(command_minimal, subprocess_run, mocker):
    mock_logger = mocker.patch("bfabric_app_runner.commands.command_exec.logger")
    subprocess_run.return_value = mocker.MagicMock(returncode=0, stdout="Resolved 1 package\n")

    execute_command_exec(command_minimal, environ={"NAME": "testing"}, log_output_level="DEBUG")

    subprocess_run.assert_called_once_with(
        ["echo", "hello world"],
        env={"NAME": "testing"},
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    mock_logger.log.assert_called_once()
    level, message = mock_logger.log.call_args[0]
    assert level == "DEBUG"
    assert "Resolved 1 package" in message


def test_execute_capture_mode_raises_and_logs_error_on_failure(command_minimal, subprocess_run, mocker):
    mock_logger = mocker.patch("bfabric_app_runner.commands.command_exec.logger")
    subprocess_run.return_value = mocker.MagicMock(returncode=2, stdout="boom\n")

    with pytest.raises(subprocess.CalledProcessError):
        execute_command_exec(command_minimal, log_output_level="DEBUG")

    mock_logger.error.assert_called_once()
    assert "boom" in mock_logger.error.call_args[0][0]
    mock_logger.log.assert_not_called()
