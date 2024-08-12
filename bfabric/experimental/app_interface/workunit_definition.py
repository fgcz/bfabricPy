from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from bfabric.entities import Workunit, Project, ExternalJob

if TYPE_CHECKING:
    from bfabric.bfabric import Bfabric


class WorkunitDefinitionData(BaseModel):
    """Encapsulates all information necessary to execute a particular workunit."""

    workunit_id: int
    project_id: int
    order_id: int | None
    parameter_values: dict[str, str]
    executable_path: Path
    input_resource_ids: list[int]
    input_dataset_ids: list[int]


class WorkunitDefinition:
    def __init__(self, data: WorkunitDefinitionData) -> None:
        self._data = data

    workunit_id = property(lambda self: self._data.workunit_id)

    @classmethod
    def from_workunit(cls, client: Bfabric, workunit: Workunit) -> WorkunitDefinition:
        data = {"workunit_id": workunit.id}
        if isinstance(workunit.container, Project):
            data["project_id"] = workunit.container.id
            data["order_id"] = None
        else:
            data["project_id"] = workunit.container.project.id
            data["order_id"] = workunit.container.id
        data["parameter_values"] = workunit.parameter_values
        data["executable_path"] = Path(workunit.application.executable["program"])
        # TODO
        data["input_resource_ids"] = []
        data["input_dataset_ids"] = []
        # TODO outputs... (But this part should be reconsidered)

        validated = WorkunitDefinitionData.model_validate(data)
        return cls(data=validated)

    @classmethod
    def from_external_job_id(cls, client: Bfabric, external_job_id: int) -> WorkunitDefinition:
        external_job = ExternalJob.find(id=external_job_id, client=client)
        return cls.from_workunit(client=client, workunit=external_job.workunit)
