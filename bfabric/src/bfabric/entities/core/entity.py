from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from loguru import logger

from bfabric.experimental import MultiQuery
from bfabric.experimental.cache.context import get_cache_stack

if TYPE_CHECKING:
    from pathlib import Path
    from collections.abc import Iterable
    from bfabric import Bfabric
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
        if self._client is None:
            msg = "Cannot generate a web URL without a client's config information."
            raise ValueError(msg)
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
        """Finds an entity by its ID, if it does not exist `None` is returned."""
        cache_stack = get_cache_stack()
        cache_entry = cache_stack.item_get(entity_type=cls, entity_id=id)
        if cache_entry:
            return cache_entry

        result = client.read(cls.ENDPOINT, obj={"id": int(id)})
        entity = cls(result[0], client=client) if len(result) == 1 else None
        cache_stack.item_put(entity_type=cls, entity_id=id, entity=entity)
        return entity

    @classmethod
    def find_all(cls, ids: list[int], client: Bfabric) -> dict[int, Self]:
        """Returns a dictionary of entities with the given IDs. The order will generally match the input, however,
        if some entities are not found they will be omitted and a warning will be logged.
        """
        cache_stack = get_cache_stack()
        ids_requested = cls.__check_ids_list(ids)

        # retrieve entities from cache and from B-Fabric as needed
        results_cached = cache_stack.item_get_all(entity_type=cls, entity_ids=ids)
        results_fresh = cls.__retrieve_entities(
            client=client, ids_requested=ids_requested, ids_cached=results_cached.keys()
        )

        cache_stack.item_put_all(entity_type=cls, entities=results_fresh)
        return cls.__ensure_results_order(ids_requested, results_cached, results_fresh)

    @classmethod
    def find_by(cls, obj: dict[str, Any], client: Bfabric, max_results: int | None = 100) -> dict[int, Self]:
        """Returns a dictionary of entities that match the given query."""
        result = client.read(cls.ENDPOINT, obj=obj, max_results=max_results)
        cache_stack = get_cache_stack()
        entities = {x["id"]: cls(x, client=client) for x in result}
        cache_stack.item_put_all(entity_type=cls, entities=entities)
        return entities

    def dump_yaml(self, path: Path) -> None:
        """Writes the entity's data dictionary to a YAML file."""
        with path.open("w") as file:
            yaml.safe_dump(self.__data_dict, file)

    @classmethod
    def load_yaml(cls, path: Path, client: Bfabric | None) -> Self:
        """Loads an entity from a YAML file."""
        with path.open("r") as file:
            data = yaml.safe_load(file)
        return cls(data, client=client)

    def __contains__(self, key: str) -> Any:
        """Checks if a key is present in the data dictionary."""
        return key in self.__data_dict

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

    @classmethod
    def __check_ids_list(cls, ids: list[int]) -> list[int]:
        """Converts the ids to a list of integers (if they are not already) and raises an error if this fails or
        there are duplicates."""
        ids_requested = [int(id) for id in ids]
        if len(ids_requested) != len(set(ids_requested)):
            duplicates = [item for item in set(ids_requested) if ids_requested.count(item) > 1]
            raise ValueError(f"Duplicate IDs are not allowed, duplicates: {duplicates}")
        return ids_requested

    @classmethod
    def __retrieve_entities(
        cls, client: Bfabric, ids_requested: list[int], ids_cached: Iterable[int]
    ) -> dict[int, Self]:
        """Retrieves entities from B-Fabric that are not already in the cache"""
        ids = list(set(ids_requested) - set(ids_cached))
        if ids:
            if len(ids) > 100:
                result = MultiQuery(client).read_multi(cls.ENDPOINT, {}, "id", ids)
            else:
                result = client.read(cls.ENDPOINT, obj={"id": ids})
            return {x["id"]: cls(x, client=client) for x in result}
        else:
            return {}

    @classmethod
    def __ensure_results_order(
        cls,
        ids_requested: list[int],
        results_cached: dict[int, Self],
        results_fresh: dict[int, Self],
    ) -> dict[int, Self]:
        """Ensures the results are in the same order as requested and prints a warning if some results are missing."""
        results = {**results_cached, **results_fresh}
        results = {entity_id: results[entity_id] for entity_id in ids_requested if entity_id in results}
        if len(results) != len(ids_requested):
            logger.warning(f"Only found {len(results)} out of {len(ids_requested)}.")
        return results
