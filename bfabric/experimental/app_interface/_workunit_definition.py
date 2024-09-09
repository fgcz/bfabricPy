# deprecated, new code will replace this
from __future__ import annotations
import warnings

warnings.warn("This module is deprecated", DeprecationWarning)


from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from pydantic import BaseModel, ConfigDict

from bfabric.entities import Workunit, Project, ExternalJob, Resource

if TYPE_CHECKING:
    from bfabric.bfabric import Bfabric


class InputResourceDefinition(BaseModel):
    id: int
    scp_address: str | None
    app_id: int
    app_name: str

    @classmethod
    def from_resource(cls, resource: Resource) -> InputResourceDefinition:
        # TODO optimize: find generic mechanism to preload entities with an arena-like cache
        scp_address = (
            f"{resource.storage.scp_prefix}{resource['relativepath']}" if resource.storage.scp_prefix else None
        )
        data = {
            "id": resource.id,
            "scp_address": scp_address,
            "app_id": resource.workunit.application.id,
            "app_name": resource.workunit.application["name"],
        }
        return cls.model_validate(data)


class WorkunitExecutionDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    parameter_values: dict[str, str]
    executable_path: Path
    input_dataset: pl.DataFrame | None
    input_resources: list[InputResourceDefinition]

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitExecutionDefinition:
        input_resources = []
        for resource in workunit.input_resources:
            input_resources.append(InputResourceDefinition.from_resource(resource))

        data = {}
        data["parameter_values"] = workunit.parameter_values
        data["executable_path"] = Path(workunit.application.executable["program"])
        data["input_dataset"] = workunit.input_dataset.to_polars() if workunit.input_dataset else None
        data["input_resources"] = input_resources
        return cls.model_validate(data)


class WorkunitRegistrationDefinition(BaseModel):
    workunit_id: int
    project_id: int
    order_id: int | None

    @classmethod
    def from_workunit(cls, workunit: Workunit) -> WorkunitRegistrationDefinition:
        data = {"workunit_id": workunit.id}
        if isinstance(workunit.container, Project):
            data["project_id"] = workunit.container.id
            data["order_id"] = None
        else:
            data["project_id"] = workunit.container.project.id
            data["order_id"] = workunit.container.id
        return cls.model_validate(data)


class WorkunitDefinition:
    def __init__(self, executon: WorkunitExecutionDefinition, registration: WorkunitRegistrationDefinition) -> None:
        self._execution = executon
        self._registration = registration

    execution = property(lambda self: self._execution)
    registration = property(lambda self: self._registration)

    # TODO keep these?
    workunit_id = property(lambda self: self._registration.workunit_id)
    project_id = property(lambda self: self._registration.project_id)
    order_id = property(lambda self: self._registration.order_id)
    parameter_values = property(lambda self: self._execution.parameter_values)
    executable_path = property(lambda self: self._execution.executable_path)
    input_resource_ids = property(lambda self: self._execution.input_resource_ids)
    input_dataset_ids = property(lambda self: self._execution.input_dataset_ids)

    @classmethod
    def from_workunit(cls, client: Bfabric, workunit: Workunit) -> WorkunitDefinition:
        return cls(
            executon=WorkunitExecutionDefinition.from_workunit(workunit),
            registration=WorkunitRegistrationDefinition.from_workunit(workunit),
        )

    @classmethod
    def from_external_job_id(cls, client: Bfabric, external_job_id: int) -> WorkunitDefinition:
        external_job = ExternalJob.find(id=external_job_id, client=client)
        return cls.from_workunit(client=client, workunit=external_job.workunit)
