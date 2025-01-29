from __future__ import annotations

from pathlib import Path
from typing import Literal, TYPE_CHECKING

import yaml
from bfabric.entities import Workunit
from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from bfabric import Bfabric


class WorkunitExecutionDefinition(BaseModel):
    """Defines the execution details of a workunit."""

    raw_parameters: dict[str, str | None]
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
        if workunit.application is None:
            raise ValueError("Workunit does not have an application")
        data = {
            "raw_parameters": workunit.parameter_values,
            "dataset": workunit.input_dataset.id if workunit.input_dataset else None,
            "resources": [r.id for r in workunit.input_resources],
        }
        return cls.model_validate(data)


class WorkunitRegistrationDefinition(BaseModel):
    """Defines the B-Fabric registration details of a workunit."""

    application_id: int
    application_name: str
    workunit_id: int
    workunit_name: str
    container_id: int
    storage_id: int
    storage_output_folder: Path
    container_type: Literal["project", "order"]

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitRegistrationDefinition:
        """Loads the workunit registration definition from the provided B-Fabric workunit."""
        data = {
            "application_id": workunit.application.id,
            "application_name": workunit.application["name"],
            "workunit_id": workunit.id,
            "workunit_name": workunit["name"],
            "container_id": workunit.container.id,
            "container_type": workunit.container.ENDPOINT,
            "storage_id": workunit.application.storage.id,
            "storage_output_folder": workunit.store_output_folder,
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
    def from_ref(
        cls, workunit: Path | int, client: Bfabric, cache_file: Path | None = None
    ) -> WorkunitDefinition:
        """Loads the workunit definition from the provided reference, which can be a path to a YAML file,
        or a workunit ID.

        If the cache file is provided and exists, it will be loaded directly instead of resolving the reference.
        Otherwise, the result will be cached to the provided file.
        :param workunit: The workunit reference, which can be a path to a YAML file, or a workunit ID.
        :param client: The B-Fabric client to use for resolving the workunit.
        :param cache_file: The path to the cache file, if any.
        """
        if cache_file is not None and cache_file.exists():
            return cls.from_yaml(cache_file)
        if isinstance(workunit, Path):
            result = cls.from_yaml(workunit)
        else:
            workunit_instance = Workunit.find(id=workunit, client=client)
            if workunit_instance is None:
                raise ValueError(f"Workunit with ID {workunit} does not exist")
            result = cls.from_workunit(workunit=workunit_instance)
        if cache_file is not None:
            cache_file.parent.mkdir(exist_ok=True, parents=True)
            result.to_yaml(cache_file)
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
