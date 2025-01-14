from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Protocol

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
    @cached_property
    def container(self: EntityProtocol) -> Project | Order:
        from bfabric.entities.project import Project
        from bfabric.entities.order import Order

        if self._client is None:
            raise ValueError("Cannot determine the container without a client.")

        result: Project | Order | None
        if self.data_dict["container"]["classname"] == Project.ENDPOINT:
            result = Project.find(id=self.data_dict["container"]["id"], client=self._client)
        elif self.data_dict["container"]["classname"] == Order.ENDPOINT:
            result = Order.find(id=self.data_dict["container"]["id"], client=self._client)
        else:
            raise ValueError(f"Unknown container classname: {self.data_dict['container']['classname']}")

        if result is None:
            raise ValueError(f"Could not find container with ID {self.data_dict['container']['id']}")

        return result
