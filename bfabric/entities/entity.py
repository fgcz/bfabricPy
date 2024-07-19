from __future__ import annotations

from typing import Any, Self

from loguru import logger

from bfabric import Bfabric


class Entity:
    ENDPOINT: str

    def __init__(self, data_dict: dict[str, Any]) -> None:
        self.__data_dict = data_dict

    @property
    def data_dict(self) -> dict[str, Any]:
        """Returns a shallow copy of the entity's data dictionary."""
        return self.__data_dict.copy()

    @classmethod
    def find(cls, id: int, client: Bfabric) -> Self | None:
        result = client.read(cls.ENDPOINT, obj={"id": id})
        return cls(result[0]) if len(result) == 1 else None

    @classmethod
    def find_all(cls, ids: list[int], client: Bfabric) -> dict[int, Self]:
        result = client.read(cls.ENDPOINT, obj={"id": ids})
        results = {x["id"]: cls(x) for x in result}
        if len(results) != len(ids):
            logger.warning(f"Only found {len(results)} out of {len(ids)}.")
        return results

    def __repr__(self) -> str:
        """Returns the string representation of the workunit."""
        return f"{self.__class__.__name__}({repr(self.__data_dict)})"

    __str__ = __repr__