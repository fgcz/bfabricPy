from __future__ import annotations

from functools import cached_property
from typing import Any

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity
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

    @property
    def _parameter_id_list(self) -> list[int]:
        """Returns the list of parameter IDs."""
        return [x["id"] for x in self.data_dict["parameter"]]

    @property
    def _resource_id_list(self) -> list[int]:
        """Returns the list of resource IDs."""
        return [x["id"] for x in self.data_dict["resource"]]

    @property
    def _input_resource_id_list(self) -> list[int]:
        """Returns the list of input resource IDs."""
        return [x["id"] for x in self.data_dict["inputresource"]]

    parameters = HasMany(entity=Parameter, ids_property="_parameter_id_list")
    resources = HasMany(entity=Resource, ids_property="_resource_id_list")
    input_resources = HasMany(entity=Resource, ids_property="_input_resource_id_list")

    @cached_property
    def parameter_values(self) -> dict[str, Any]:
        return {p.key: p.value for p in self.parameters.list}
