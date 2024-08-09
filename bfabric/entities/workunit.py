from __future__ import annotations

from functools import cached_property
from typing import Any, TYPE_CHECKING

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric.entities.project import Project
    from bfabric.entities.order import Order


class Workunit(Entity):
    """Immutable representation of a single workunit in B-Fabric.
    :param data_dict: The dictionary representation of the workunit.
    """

    ENDPOINT = "workunit"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    application = HasOne(entity="Application", bfabric_field="application")
    parameters = HasMany(entity="Parameter", bfabric_field="parameter")
    resources = HasMany(entity="Resource", bfabric_field="resource")
    input_resources = HasMany(entity="Resource", bfabric_field="inputresource", optional=True)
    input_dataset = HasOne(entity="Dataset", bfabric_field="inputdataset", optional=True)

    @cached_property
    def parameter_values(self) -> dict[str, Any]:
        return {p.key: p.value for p in self.parameters.list}

    @cached_property
    def container(self) -> Project | Order:
        from bfabric.entities.project import Project
        from bfabric.entities.order import Order

        if self.data_dict["container"]["classname"] == Project.ENDPOINT:
            return Project.find(id=self.data_dict["container"]["id"], client=self._client)
        elif self.data_dict["container"]["classname"] == Order.ENDPOINT:
            return Order.find(id=self.data_dict["container"]["id"], client=self._client)
        else:
            raise ValueError(f"Unknown container classname: {self.data_dict['container']['classname']}")
