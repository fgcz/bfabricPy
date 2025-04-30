from typing import assert_never

from bfabric_app_runner.actions.types import (
    ActionDispatch,
    ActionInputs,
    ActionProcess,
    ActionOutputs,
    ActionRun,
    ActionGeneric,
)


def execute(action: ActionGeneric) -> None:
    """Executes any action."""
    match action:
        case ActionDispatch():
            execute_dispatch(action)
        case ActionRun():
            execute_run(action)
        case ActionInputs():
            execute_inputs(action)
        case ActionProcess():
            execute_process(action)
        case ActionOutputs():
            execute_outputs(action)
        case _:
            assert_never(action)


def execute_dispatch(action: ActionDispatch) -> None:
    """Executes a dispatch action."""
    pass


def execute_run(action: ActionRun) -> None:
    """Executes a run action."""
    pass


def execute_inputs(action: ActionInputs) -> None:
    """Executes an inputs action."""
    pass


def execute_process(action: ActionProcess) -> None:
    """Executes a process action."""
    pass


def execute_outputs(action: ActionOutputs) -> None:
    """Executes an outputs action."""
    pass
