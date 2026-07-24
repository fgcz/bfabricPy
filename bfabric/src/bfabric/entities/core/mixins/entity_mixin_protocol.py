from typing import Any, Protocol


class EntityProtocol(Protocol):
    @property
    def bfabric_instance(self) -> str: ...

    @property
    def data_dict(self) -> dict[str, Any]: ...
