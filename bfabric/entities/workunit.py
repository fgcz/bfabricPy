from __future__ import annotations

from typing import Any

from bfabric import Bfabric
from bfabric.entities.entity import Entity
from bfabric.entities.parameter import Parameter


class Workunit(Entity):
    """Immutable representation of a single workunit in B-Fabric.
    :param data_dict: The dictionary representation of the workunit.
    """

    ENDPOINT = "workunit"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    @property
    def parameter_id_list(self) -> list[int]:
        """Returns the list of parameter IDs."""
        return [x["id"] for x in self.data_dict["parameter"]]

    def get_parameters(self, client: Bfabric) -> dict[int, Parameter]:
        """Returns the list of parameter objects."""
        return Parameter.find_all(self.parameter_id_list, client=client)

    def get_parameter_values(self, client: Bfabric) -> dict[str, Any]:
        """Returns the dictionary of parameter keys and values."""
        return {x.key: x.value for x in self.get_parameters(client).values()}
