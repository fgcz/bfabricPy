from pathlib import Path

from bfabric_app_runner.commands.command_python_env import execute_command_python_env
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


def test_execute(mocker):
    execute_command = mocker.patch("bfabric_app_runner.commands.command_python_env.execute_command_exec")
    args = ["hello", "world"]
    cmd = CommandPythonEnv(pylock=Path("/test/pylock"), command="bash -c 'echo $1 $2'", python_version="3.13")
    execute_command_python_env(cmd, *args)
    execute_command.assert_called_once_with(
        CommandExec(
            command="uv run -p 3.13 --no-project --isolated --with /test/pylock bash -c 'echo $1 $2'",
            env={},
            prepend_paths=[],
        ),
        "hello",
        "world",
    )
