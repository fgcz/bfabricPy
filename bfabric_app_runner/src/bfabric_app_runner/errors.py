import shlex


class CommandFailedError(RuntimeError):
    """A command launched by the app runner exited non-zero.

    Subclasses ``RuntimeError`` so ``use_client`` reports it as one ``Error: ...`` line without a
    traceback: the command already wrote its own diagnostics, which a traceback would only bury.
    """

    def __init__(self, command_args: list[str], returncode: int) -> None:
        super().__init__(f"Command failed with exit code {returncode}: {shlex.join(command_args)}")
