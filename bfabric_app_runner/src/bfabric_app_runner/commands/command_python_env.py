import shlex

from bfabric_app_runner.commands.command_exec import execute_command_exec
from bfabric_app_runner.specs.app.commands_spec import CommandPythonEnv, CommandExec


def execute_command_python_env(command: CommandPythonEnv, *args: str) -> None:
    """Executes the command with the provided arguments."""
    # TODO this is the initial version, we want this more robust with caching etc in the future, so
    #      it works fully offline as well (the idea would be that the environment gets specified but you can
    #      prepare it ahead of time).
    main_command = ["uv", "run", "-p", command.python_version, "--with", str(command.pylock)]
    if command.local_extra_deps:
        main_command.extend(["--with", ",".join(command.local_extra_deps)])
    main_command.extend(shlex.split(command.command))
    exec_command = CommandExec(command=shlex.join(main_command), env=command.env, prepend_paths=command.prepend_paths)
    execute_command_exec(exec_command, *args)
