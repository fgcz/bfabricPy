from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.core.mixins.user_created_mixin import UserCreatedMixin

if TYPE_CHECKING:
    from bfabric.entities import WorkflowTemplateStep


class WorkflowTemplate(Entity, UserCreatedMixin):
    ENDPOINT = "workflowtemplate"

    workflow_template_steps: HasMany[WorkflowTemplateStep] = HasMany(bfabric_field="workflowtemplatestep")
