from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from bfabric import Bfabric
from bfabric.entities import Workunit


class WorkunitExecutionDefinition(BaseModel):
    """Defines the execution details of a workunit."""

    model_config = ConfigDict(extra="forbid")

    raw_parameters: dict[str, str | None]
    executable: Path
    dataset: int | None = None
    resources: list[int] = []

    @model_validator(mode="after")
    def mutually_exclusive_dataset_resources(self) -> WorkunitExecutionDefinition:
        """Validates that dataset and resources are mutually exclusive."""
        if self.dataset is not None and self.resources:
            raise ValueError("dataset and resources are mutually exclusive")
        if self.dataset is None and not self.resources:
            raise ValueError("either dataset or resources must be provided")
        return self

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitExecutionDefinition:
        """Loads the workunit execution definition from the provided B-Fabric workunit."""
        data = {
            "raw_parameters": workunit.parameter_values,
            "executable": workunit.application.executable["program"],
            "dataset": workunit.input_dataset.id if workunit.input_dataset else None,
            "resources": [r.id for r in workunit.input_resources],
        }
        return cls.model_validate(data)


class WorkunitRegistrationDefinition(BaseModel):
    """Defines the B-Fabric registration details of a workunit."""

    model_config = ConfigDict(extra="forbid")

    workunit_id: int
    container_id: int
    container_type: Literal["project", "order"]

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitRegistrationDefinition:
        """Loads the workunit registration definition from the provided B-Fabric workunit."""
        data = {
            "workunit_id": workunit.id,
            "container_id": workunit.container.id,
            "container_type": workunit.container.ENDPOINT,
        }
        return cls.model_validate(data)


class WorkunitDefinition(BaseModel):
    """Defines a workunit, including details on how to execute it and where to register it.
    This class provides a simple way for developers to persist and run workunit definitions from YAML files, as well as
    loading the same from B-Fabric workunits. This abstraction ensures easier development and testing of applications.
    """

    execution: WorkunitExecutionDefinition
    registration: WorkunitRegistrationDefinition | None

    @classmethod
    def from_ref(cls, workunit: Path | int, client: Bfabric) -> WorkunitDefinition:
        """Loads the workunit definition from the provided reference,
        which can be a path to a YAML file, or a workunit ID.
        """
        if isinstance(workunit, Path):
            return cls.from_yaml(workunit)
        else:
            workunit = Workunit.find(id=workunit, client=client)
            return cls.from_workunit(workunit)

    @classmethod
    def from_ref_cached(cls, workunit: Path | int, file: Path, client: Bfabric) -> WorkunitDefinition:
        """Loads the workunit definition from the provided reference, caching the result to the provided file.
        If the cache file exists, it will be loaded directly instead of resolving the reference.
        """
        if file.exists():
            return cls.from_yaml(file)
        result = cls.from_ref(workunit=workunit, client=client)
        result.to_yaml(file)
        return result

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitDefinition:
        """Loads the workunit definition from the provided B-Fabric workunit."""
        return cls(
            execution=WorkunitExecutionDefinition.from_workunit(workunit),
            registration=WorkunitRegistrationDefinition.from_workunit(workunit),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> WorkunitDefinition:
        """Loads the workunit definition from the provided path."""
        data = yaml.safe_load(path.read_text())
        return cls.model_validate(data)

    def to_yaml(self, path: Path) -> None:
        """Writes the workunit definition to the provided path."""
        path.write_text(yaml.safe_dump(self.model_dump(mode="json")))
