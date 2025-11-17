from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bfabric import Bfabric
    from typing import Any


class EntityProtocol(Protocol):
    @property
    def _client(self) -> Bfabric | None: ...

    @property
    def data_dict(self) -> dict[str, Any]: ...
