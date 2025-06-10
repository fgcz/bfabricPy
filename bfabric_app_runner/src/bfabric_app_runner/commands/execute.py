from typing import assert_never

from bfabric_app_runner.commands.command_docker import execute_command_docker
from bfabric_app_runner.commands.command_exec import execute_command_exec
from bfabric_app_runner.commands.command_python_env import execute_command_python_env
from bfabric_app_runner.commands.command_shell import execute_command_shell
from bfabric_app_runner.specs.app.commands_spec import (
    Command,
    CommandShell,
    CommandExec,
    CommandDocker,
    CommandPythonEnv,
)


def execute_command(command: Command, *args: str) -> None:
    """Executes the given command with the provided arguments."""
    command_type = type(command)
    if issubclass(command_type, CommandShell):
        execute_command_shell(command, *args)
    elif issubclass(command_type, CommandExec):
        execute_command_exec(command, *args)
    elif issubclass(command_type, CommandDocker):
        execute_command_docker(command, *args)
    elif issubclass(command_type, CommandPythonEnv):
        execute_command_python_env(command, *args)
    else:
        assert_never(command_type)
