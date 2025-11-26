from typing import Protocol, Any

from bfabric import Bfabric


class EntityProtocol(Protocol):
    @property
    def _client(self) -> Bfabric | None: ...

    @property
    def data_dict(self) -> dict[str, Any]: ...
