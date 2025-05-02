from enum import Enum
from pathlib import Path
from typing import Literal, Annotated

from pydantic import BaseModel, Field


class Action(str, Enum):
    run = "run"
    dispatch = "dispatch"
    inputs = "inputs"
    process = "process"
    outputs = "outputs"


class ActionDispatch(BaseModel):
    action: Literal[Action.dispatch] = Action.dispatch
    work_dir: Path


class ActionRun(BaseModel):
    action: Literal[Action.run] = Action.run
    work_dir: Path  # generic function
    chunk: str | None = None  # generic function -> script
    ssh_user: str | None = None  # generic param -> env/config file
    filter: str | None = None  # specific
    app_ref: Path | str
    force_storage: Path | None = None  # generic param -> env/config file


class ActionInputs(BaseModel):
    action: Literal[Action.inputs] = Action.inputs
    work_dir: Path
    chunk: str | None = None
    ssh_user: str | None = None
    filter: str | None = None


class ActionProcess(BaseModel):
    action: Literal[Action.process] = Action.process
    work_dir: Path
    app_ref: Path | str
    chunk: str | None = None


class ActionOutputs(BaseModel):
    action: Literal[Action.outputs] = Action.outputs
    work_dir: Path
    workunit_ref: int | Path
    chunk: str | None = None
    ssh_user: str | None = None
    force_storage: Path | None = None


ActionGeneric = Annotated[
    ActionRun | ActionDispatch | ActionInputs | ActionProcess | ActionOutputs, Field(discriminator="action")
]
