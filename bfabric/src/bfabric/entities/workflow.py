from __future__ import annotations

from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_container_mixin import HasContainerMixin
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.core.has_one import HasOne
from bfabric.entities.core.user_created_mixin import UserCreatedMixin

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.workflowtemplate import WorkflowTemplate
    from bfabric.entities.workflowstep import WorkflowStep


class Workflow(Entity, HasContainerMixin, UserCreatedMixin):
    ENDPOINT = "workflow"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    workflow_steps: HasMany[WorkflowStep] = HasMany(entity="WorkflowStep", bfabric_field="workflowstep")
    workflow_template: HasOne[WorkflowTemplate] = HasOne(
        entity="WorkflowTemplate", bfabric_field="workflowtemplate", optional=True
    )
