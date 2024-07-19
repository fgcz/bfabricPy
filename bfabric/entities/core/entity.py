from __future__ import annotations

from loguru import logger

from bfabric import Bfabric
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Self


class Entity:
    ENDPOINT: str = ""

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        self.__data_dict = data_dict
        self.__client = client

    @property
    def data_dict(self) -> dict[str, Any]:
        """Returns a shallow copy of the entity's data dictionary."""
        return self.__data_dict.copy()

    @property
    def _client(self) -> Bfabric | None:
        """Returns the client associated with the entity."""
        return self.__client

    @classmethod
    def find(cls, id: int, client: Bfabric) -> Self | None:
        result = client.read(cls.ENDPOINT, obj={"id": id})
        return cls(result[0], client=client) if len(result) == 1 else None

    @classmethod
    def find_all(cls, ids: list[int], client: Bfabric) -> dict[int, Self]:
        if len(ids) > 100:
            # TODO use paginated read if more than 100 ids
            raise NotImplementedError("Pagination not yet implemented here.")
        result = client.read(cls.ENDPOINT, obj={"id": ids})
        results = {x["id"]: cls(x, client=client) for x in result}
        if len(results) != len(ids):
            logger.warning(f"Only found {len(results)} out of {len(ids)}.")
        return results

    def __repr__(self) -> str:
        """Returns the string representation of the workunit."""
        return f"{self.__class__.__name__}({repr(self.__data_dict)}, client={repr(self.__client)})"

    __str__ = __repr__
