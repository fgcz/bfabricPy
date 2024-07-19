from __future__ import annotations

from typing import Any

from bfabric.entities.entity import Entity


class Workunit(Entity):
    """Immutable representation of a single workunit in B-Fabric.
    :param data_dict: The dictionary representation of the workunit.
    """

    ENDPOINT = "workunit"

    def __init__(self, data_dict: dict[str, Any]) -> None:
        super().__init__(data_dict)

    @property
    def parameter_id_list(self) -> list[int]:
        """Returns the list of parameter IDs."""
        return [x["id"] for x in self.data_dict["parameter"]]
