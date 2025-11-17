from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric.entities.order import Order
    from bfabric import Bfabric
    from bfabric.entities.project import Project
    from typing import Any


class EntityProtocol(Protocol):
    @property
    def _client(self) -> Bfabric | None: ...

    @property
    def data_dict(self) -> dict[str, Any]: ...


class HasContainerMixin:
    container: HasOne[Order | Project] = HasOne(bfabric_field="container")
