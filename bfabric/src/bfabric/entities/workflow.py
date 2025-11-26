from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.core.has_one import HasOne
from bfabric.entities.core.mixins.user_created_mixin import UserCreatedMixin

if TYPE_CHECKING:
    from bfabric.entities import Order, Project, WorkflowStep, WorkflowTemplate


class Workflow(Entity, UserCreatedMixin):
    ENDPOINT = "workflow"

    container: HasOne[Order | Project] = HasOne(bfabric_field="container")
    workflow_steps: HasMany[WorkflowStep] = HasMany(bfabric_field="workflowstep")
    workflow_template: HasOne[WorkflowTemplate] = HasOne(bfabric_field="workflowtemplate", optional=True)
