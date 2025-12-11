from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric.entities.executable import Executable
    from bfabric.entities.workunit import Workunit


class ExternalJob(Entity):
    ENDPOINT = "externaljob"

    executable: HasOne[Executable] = HasOne(bfabric_field="executable")

    @cached_property
    def workunit(self) -> Workunit | None:
        from bfabric.entities.workunit import Workunit

        if self.data_dict["cliententityclassname"] == "Workunit":
            if self._client is None:
                raise ValueError("Client must be set to resolve Workunit")

            client_entity_id = self.data_dict["cliententityid"]
            if not isinstance(client_entity_id, int):
                raise ValueError("Invalid client entity ID")
            return Workunit.find(id=client_entity_id, client=self._client)
        else:
            return None
