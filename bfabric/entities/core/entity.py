from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from bfabric import Bfabric
from bfabric.experimental import MultiQuery

if TYPE_CHECKING:
    from typing import Any, Self


class Entity:
    ENDPOINT: str = ""

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        self.__data_dict = data_dict
        self.__client = client

    @property
    def id(self) -> int:
        """Returns the entity's ID."""
        return int(self.__data_dict["id"])

    @property
    def web_url(self) -> str:
        return f"{self._client.config.base_url}/{self.ENDPOINT}/show.html?id={self.id}"

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
        result = client.read(cls.ENDPOINT, obj={"id": int(id)})
        return cls(result[0], client=client) if len(result) == 1 else None

    @classmethod
    def find_all(cls, ids: list[int], client: Bfabric) -> dict[int, Self]:
        ids = [int(id) for id in ids]
        if len(ids) > 100:
            result = MultiQuery(client).read_multi(cls.ENDPOINT, {}, "id", ids)
        else:
            result = client.read(cls.ENDPOINT, obj={"id": ids})
        results = {x["id"]: cls(x, client=client) for x in result}
        if len(results) != len(ids):
            logger.warning(f"Only found {len(results)} out of {len(ids)}.")
        return results

    @classmethod
    def find_by(cls, obj: dict[str, Any], client: Bfabric, max_results: int | None = 100) -> dict[int, Self]:
        result = client.read(cls.ENDPOINT, obj=obj, max_results=max_results)
        return {x["id"]: cls(x, client=client) for x in result}

    def __getitem__(self, key: str) -> Any:
        """Returns the value of a key in the data dictionary."""
        return self.__data_dict[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Returns the value of a key in the data dictionary, or a default value if the key is not present."""
        return self.__data_dict.get(key, default)

    def __lt__(self, other: Entity) -> bool:
        """Compares the entity with another entity based on their IDs."""
        if self.ENDPOINT != other.ENDPOINT:
            return NotImplemented
        return self.id < other.id

    def __repr__(self) -> str:
        """Returns the string representation of the workunit."""
        return f"{self.__class__.__name__}({repr(self.__data_dict)}, client={repr(self.__client)})"

    __str__ = __repr__
