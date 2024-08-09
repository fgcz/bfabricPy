from __future__ import annotations

from functools import cached_property
from typing import Any

from bfabric import Bfabric
from bfabric.entities import Application
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.parameter import Parameter
from bfabric.entities.resource import Resource


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
    input_resources = HasMany(entity="Resource", bfabric_field="inputresource")

    @cached_property
    def parameter_values(self) -> dict[str, Any]:
        return {p.key: p.value for p in self.parameters.list}
