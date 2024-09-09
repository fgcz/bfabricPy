from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from bfabric.entities import Workunit


class WorkunitExecutionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_parameters: dict[str, str | None]
    executable: Path
    dataset: int | None = None
    resources: list[int] = []

    @model_validator(mode="after")
    def mutually_exclusive_dataset_resources(self) -> WorkunitExecutionDefinition:
        if self.dataset is not None and self.resources:
            raise ValueError("dataset and resources are mutually exclusive")
        if self.dataset is None and not self.resources:
            raise ValueError("either dataset or resources must be provided")
        return self

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitExecutionDefinition:
        data = {
            "raw_parameters": workunit.parameter_values,
            "executable": workunit.application.executable["program"],
            "dataset": workunit.input_dataset.id if workunit.input_dataset else None,
            "resources": [r.id for r in workunit.input_resources],
        }
        return cls.model_validate(data)


class WorkunitRegistrationDefinition(BaseModel):
    workunit_id: int
    container_id: int
    container_type: Literal["project", "order"]

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitRegistrationDefinition:
        data = {
            "workunit_id": workunit.id,
            "container_id": workunit.container.id,
            "container_type": workunit.container.ENDPOINT,
        }
        return cls.model_validate(data)


class WorkunitDefinition(BaseModel):
    execution: WorkunitExecutionDefinition
    registration: WorkunitRegistrationDefinition | None

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitDefinition:
        return cls(
            execution=WorkunitExecutionDefinition.from_workunit(workunit),
            registration=WorkunitRegistrationDefinition.from_workunit(workunit),
        )
