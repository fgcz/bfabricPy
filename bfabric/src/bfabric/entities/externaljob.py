from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric.entities.executable import Executable
    from bfabric.entities.workunit import Workunit


class _ClientEntityRef(BaseModel):
    model_config: ConfigDict = ConfigDict(str_to_lower=True)  # pyright: ignore[reportIncompatibleVariableOverride]
    client_entity_classname: str = Field(alias="cliententityclassname")
    client_entity_id: int = Field(alias="cliententityid")


class ExternalJob(Entity):
    ENDPOINT = "externaljob"

    executable: HasOne[Executable] = HasOne(bfabric_field="executable")

    @cached_property
    def client_entity(self) -> Entity | None:
        # TODO the most clean solution would be to extract the Reference loading functionality from References
        #      into a separate class which can be reused here.
        ref = _ClientEntityRef.model_validate(self.data_dict)
        if self._client is None:
            raise ValueError("Client must be set to resolve client entity")
        return self._client.reader.read_id(
            entity_type=ref.client_entity_classname,
            entity_id=ref.client_entity_id,
            bfabric_instance=self.bfabric_instance,
        )

    @cached_property
    def workunit(self) -> Workunit | None:
        from bfabric.entities.workunit import Workunit

        entity = self.client_entity
        if isinstance(entity, Workunit):
            return entity
        else:
            return None
