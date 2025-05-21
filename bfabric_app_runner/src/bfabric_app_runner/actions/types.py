from __future__ import annotations
from enum import Enum
from pathlib import Path  # noqa
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
    read_only: bool = False


class ActionRun(FromConfigFile):
    action: Literal[Action.run] = Action.run
    work_dir: Path
    chunk: str | None = None
    ssh_user: str | None = None
    filter: str | None = None
    app_ref: Path | str
    force_storage: Path | None = None
    read_only: bool = False
    workunit_ref: int | Path


class ActionInputs(FromConfigFile):
    action: Literal[Action.inputs] = Action.inputs
    work_dir: Path
    chunk: str | None = None
    ssh_user: str | None = None
    filter: str | None = None

    @classmethod
    def from_action_run(cls, action_run: ActionRun, chunk: str | None) -> ActionInputs:
        """Returns an ActionInputs object from an ActionRun object."""
        return ActionInputs(
            work_dir=action_run.work_dir,
            chunk=action_run.chunk if chunk is None else chunk,
            ssh_user=action_run.ssh_user,
            filter=action_run.filter,
        )


class ActionProcess(FromConfigFile):
    action: Literal[Action.process] = Action.process
    work_dir: Path
    app_ref: Path | str
    chunk: str | None = None

    @classmethod
    def from_action_run(cls, action_run: ActionRun, chunk: str | None) -> ActionProcess:
        """Returns an ActionProcess object from an ActionRun object."""
        return ActionProcess(
            work_dir=action_run.work_dir,
            app_ref=action_run.app_ref,
            chunk=action_run.chunk if chunk is None else chunk,
        )


class ActionOutputs(FromConfigFile):
    action: Literal[Action.outputs] = Action.outputs
    work_dir: Path
    workunit_ref: int | Path
    app_ref: Path | str
    chunk: str | None = None
    ssh_user: str | None = None
    force_storage: Path | None = None
    read_only: bool = False

    @classmethod
    def from_action_run(cls, action_run: ActionRun, chunk: str | None) -> ActionOutputs:
        """Returns an ActionOutputs object from an ActionRun object."""
        return ActionOutputs(
            work_dir=action_run.work_dir,
            app_ref=action_run.app_ref,
            chunk=action_run.chunk if chunk is None else chunk,
            ssh_user=action_run.ssh_user,
            force_storage=action_run.force_storage,
            read_only=action_run.read_only,
            workunit_ref=action_run.workunit_ref,
        )


ActionGeneric = Annotated[
    ActionRun | ActionDispatch | ActionInputs | ActionProcess | ActionOutputs, Field(discriminator="action")
]
