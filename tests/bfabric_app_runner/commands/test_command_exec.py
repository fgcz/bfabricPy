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
