from bfabric_app_runner.commands.command_exec import execute_command_exec
from bfabric_app_runner.specs.app.commands_spec import CommandShell, CommandExec


def execute_command_shell(command: CommandShell, *args: str) -> None:
    """Executes the command with the provided arguments."""
    execute_command_exec(CommandExec(command=command.command), *args)
