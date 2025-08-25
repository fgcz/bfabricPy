from __future__ import annotations

from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.core.user_created_mixin import UserCreatedMixin

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import WorkflowTemplateStep


class WorkflowTemplate(Entity, UserCreatedMixin):
    ENDPOINT = "workflowtemplate"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    workflow_template_steps: HasMany[WorkflowTemplateStep] = HasMany(
        entity="WorkflowTemplateStep", bfabric_field="workflowtemplatestep"
    )
