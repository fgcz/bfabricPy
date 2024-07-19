from __future__ import annotations

from functools import cached_property
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
    def _parameter_id_list(self) -> list[int]:
        """Returns the list of parameter IDs."""
        return [x["id"] for x in self.data_dict["parameter"]]

    @cached_property
    def parameters(self) -> dict[int, Parameter]:
        """Returns the list of parameter objects."""
        return Parameter.find_all(ids=self._parameter_id_list, client=self._client)

    @cached_property
    def parameter_values(self) -> dict[str, Any]:
        return {p.key: p.value for p in self.parameters.values()}
