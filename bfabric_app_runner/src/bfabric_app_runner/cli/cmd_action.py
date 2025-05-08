from typing import Annotated

import cyclopts
from cyclopts import Parameter

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.actions.execute import execute
from bfabric_app_runner.actions.types import ActionInputs, ActionProcess, ActionOutputs, ActionRun, ActionDispatch

app = cyclopts.App()


@use_client
def cmd_action_dispatch(*, action: Annotated[ActionDispatch, Parameter(name="*")], client: Bfabric) -> None:
    """Dispatches a workunit definition."""
    execute(action, client=client)


@use_client
def cmd_action_run_all(*, action: Annotated[ActionRun, Parameter(name="*")], client: Bfabric) -> None:
    """Runs all stages of an app that has been dispatched."""
    execute(action, client=client)


@use_client
def cmd_action_inputs(*, action: Annotated[ActionInputs, Parameter(name="*")], client: Bfabric) -> None:
    """Prepares the input files by downloading and generating them (if necessary)."""
    execute(action, client=client)


@use_client
def cmd_action_process(*, action: Annotated[ActionProcess, Parameter(name="*")], client: Bfabric) -> None:
    """Processes a chunk."""
    execute(action, client=client)


@use_client
def cmd_action_outputs(*, action: Annotated[ActionOutputs, Parameter(name="*")], client: Bfabric) -> None:
    """Registers the output files of a chunk."""
    execute(action, client=client)
