from __future__ import annotations

from functools import cached_property
from typing import Any, TYPE_CHECKING

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity

if TYPE_CHECKING:
    from bfabric.entities.workunit import Workunit


class ExternalJob(Entity):
    ENDPOINT = "externaljob"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    @cached_property
    def workunit(self) -> Workunit | None:
        from bfabric.entities.workunit import Workunit

        if self.data_dict["cliententityclassname"] == "Workunit":
            return Workunit.find(id=self.data_dict["cliententityid"], client=self._client)
        else:
            return None
