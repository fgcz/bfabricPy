import subprocess
from pathlib import Path

import pytest

from bfabric_app_runner.commands.command_exec import execute_command_exec
from bfabric_app_runner.errors import CommandFailedError
from bfabric_app_runner.specs.app.commands_spec import CommandExec


@pytest.fixture
def command_minimal():
    return CommandExec(command="echo 'hello world'")


@pytest.fixture
def subprocess_run(mocker):
    return mocker.patch("subprocess.run")


class TestStreamedOutput:
    """The app's own commands, whose output goes straight to the parent's stdout/stderr."""

    @pytest.fixture
    def command_full(self):
        return CommandExec(
            command='bash -c \'echo "hello $NAME" && echo "$PATH"\'',
            env={"NAME": "sun"},
            prepend_paths=[Path("/usr/local/bin"), Path("~/bin")],
        )

    def test_execute_minimal(self, command_minimal, subprocess_run):
        execute_command_exec(command_minimal, "hello", "world", environ={"NAME": "testing"})
        subprocess_run.assert_called_once_with(
            ["echo", "hello world", "hello", "world"],
            env={"NAME": "testing"},
            check=True,
        )

    def test_execute_full(self, mocker, command_full, subprocess_run):
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

    def test_failure_raises_command_failed_error(self, command_minimal, subprocess_run):
        subprocess_run.side_effect = subprocess.CalledProcessError(3, ["echo", "hello world"])

        with pytest.raises(CommandFailedError) as exc_info:
            execute_command_exec(command_minimal, environ={"NAME": "testing"})

        assert "exit code 3" in str(exc_info.value)
        assert "echo 'hello world'" in str(exc_info.value)

    def test_failure_is_a_runtime_error_keeping_the_original_cause(self, command_minimal, subprocess_run):
        """``use_client`` renders ``RuntimeError`` without a traceback; ``__cause__`` keeps it recoverable."""
        subprocess_run.side_effect = subprocess.CalledProcessError(3, ["echo", "hello world"])

        with pytest.raises(RuntimeError) as exc_info:
            execute_command_exec(command_minimal, environ={"NAME": "testing"})

        assert isinstance(exc_info.value.__cause__, subprocess.CalledProcessError)


class TestCapturedOutput:
    """Provisioning commands, whose output is captured and re-emitted through the logger."""

    @pytest.fixture
    def mock_logger(self, mocker):
        return mocker.patch("bfabric_app_runner.commands.command_exec.logger")

    def test_output_is_logged_at_the_requested_level(self, command_minimal, subprocess_run, mock_logger, mocker):
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
        assert mock_logger.log.call_args_list == [mocker.call("DEBUG", "Resolved 1 package")]

    def test_multiline_output_is_logged_one_record_per_line(self, command_minimal, subprocess_run, mock_logger, mocker):
        subprocess_run.return_value = mocker.MagicMock(returncode=0, stdout="first\nsecond\nthird\n")

        execute_command_exec(command_minimal, log_output_level="DEBUG")

        assert mock_logger.log.call_args_list == [
            mocker.call("DEBUG", "first"),
            mocker.call("DEBUG", "second"),
            mocker.call("DEBUG", "third"),
        ]

    def test_failure_raises_command_failed_error_and_logs_output_at_error(
        self, command_minimal, subprocess_run, mock_logger, mocker
    ):
        subprocess_run.return_value = mocker.MagicMock(returncode=2, stdout="boom\nbang\n")

        with pytest.raises(CommandFailedError) as exc_info:
            execute_command_exec(command_minimal, log_output_level="DEBUG")

        assert "exit code 2" in str(exc_info.value)
        assert "echo 'hello world'" in str(exc_info.value)
        assert mock_logger.log.call_args_list == [mocker.call("ERROR", "boom"), mocker.call("ERROR", "bang")]
