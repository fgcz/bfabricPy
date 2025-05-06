from enum import Enum
from pathlib import Path
from typing import Literal, Annotated

from pydantic import Field

from bfabric_app_runner.actions.config_file import FromConfigFile


class Action(str, Enum):
    run = "run"
    dispatch = "dispatch"
    inputs = "inputs"
    process = "process"
    outputs = "outputs"


class ActionDispatch(FromConfigFile):
    action: Literal[Action.dispatch] = Action.dispatch
    work_dir: Path
    app_ref: Path | str
    workunit_ref: int | Path


class ActionRun(FromConfigFile):
    action: Literal[Action.run] = Action.run
    work_dir: Path
    chunk: str | None = None
    ssh_user: str | None = None
    filter: str | None = None
    app_ref: Path | str
    force_storage: Path | None = None


class ActionInputs(FromConfigFile):
    action: Literal[Action.inputs] = Action.inputs
    work_dir: Path
    chunk: str | None = None
    ssh_user: str | None = None
    filter: str | None = None


class ActionProcess(FromConfigFile):
    action: Literal[Action.process] = Action.process
    work_dir: Path
    app_ref: Path | str
    chunk: str | None = None


class ActionOutputs(FromConfigFile):
    action: Literal[Action.outputs] = Action.outputs
    work_dir: Path
    workunit_ref: int | Path
    app_ref: Path | str
    chunk: str | None = None
    ssh_user: str | None = None
    force_storage: Path | None = None


ActionGeneric = Annotated[
    ActionRun | ActionDispatch | ActionInputs | ActionProcess | ActionOutputs, Field(discriminator="action")
]
