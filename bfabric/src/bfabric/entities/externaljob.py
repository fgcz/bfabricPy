from __future__ import annotations

from functools import cached_property
from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.workunit import Workunit
    from bfabric.entities.executable import Executable


class ExternalJob(Entity):
    ENDPOINT = "externaljob"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    executable: HasOne[Executable] = HasOne(entity="Executable", bfabric_field="executable")

    @cached_property
    def workunit(self) -> Workunit | None:
        from bfabric.entities.workunit import Workunit

        if self.data_dict["cliententityclassname"] == "Workunit":
            if self._client is None:
                raise ValueError("Client must be set to resolve Workunit")

            return Workunit.find(id=self.data_dict["cliententityid"], client=self._client)
        else:
            return None
