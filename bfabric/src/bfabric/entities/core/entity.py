from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import yaml
from loguru import logger

from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric import Bfabric
    from typing import Any, Self


class Entity:
    # TODO this should be deprecated in favor of classname or moving the .find stuff into mixin
    ENDPOINT: str = ""

    def __init__(
        self, data_dict: dict[str, Any], client: Bfabric | None, *, bfabric_instance: str | None = None
    ) -> None:
        self.__data_dict = data_dict
        self.__client = client
        self.__bfabric_instance = bfabric_instance

    @property
    def classname(self) -> str:
        """The entity's classname."""
        return self.__data_dict["classname"]

    @property
    def id(self) -> int:
        """The entity's ID."""
        return int(self.__data_dict["id"])

    @property
    def uri(self) -> EntityUri:
        """The entity's URI."""
        if self.__bfabric_instance is None and self._client is None:
            msg = "Cannot generate a URI without a client's config information."
            raise ValueError(msg)
        bfabric_instance = self.__bfabric_instance or self._client.config.base_url
        return EntityUri.from_components(
            bfabric_instance=bfabric_instance, entity_type=self.classname, entity_id=self.id
        )

    @property
    def web_url(self) -> str:
        # TODO delete this function later (and document deprecation)
        warnings.warn("Entity.web_url is deprecated, use str(Entity.uri) instead.", DeprecationWarning, stacklevel=2)
        return str(self.uri)

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
        from bfabric.entities.core.entity_reader import EntityReader

        reader = EntityReader(client=client)
        uri = EntityUri.from_components(bfabric_instance=client.config.base_url, entity_type=cls.ENDPOINT, entity_id=id)
        entity = reader.read_uri(uri=uri)
        if entity is None:
            return None
        return cls(entity.data_dict, client=entity._client)

    @classmethod
    def find_all(cls, ids: list[int], client: Bfabric) -> dict[int, Self]:
        """Returns a dictionary of entities with the given IDs. The order will generally match the input, however,
        if some entities are not found they will be omitted and a warning will be logged.
        """
        from bfabric.entities.core.entity_reader import EntityReader

        reader = EntityReader(client=client)
        uris = [
            EntityUri.from_components(bfabric_instance=client.config.base_url, entity_type=cls.ENDPOINT, entity_id=id)
            for id in ids
        ]
        results = reader.read_uris(uris=uris)
        results = {
            uri.components.entity_id: cls(entity.data_dict, client=entity._client)
            for uri, entity in results.items()
            if entity is not None
        }
        return cls.__ensure_results_order(ids, results)

    @classmethod
    def find_by(cls, obj: dict[str, Any], client: Bfabric, max_results: int | None = 100) -> dict[int, Self]:
        """Returns a dictionary of entities that match the given query."""
        from bfabric.entities.core.entity_reader import EntityReader

        reader = EntityReader(client=client)
        results = reader.query_by(entity_type=cls.ENDPOINT, obj=obj, max_results=max_results)
        return {
            uri.components.entity_id: cls(entity.data_dict, client=entity._client) for uri, entity in results.items()
        }

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
    def __ensure_results_order(
        cls,
        ids_requested: list[int],
        results: dict[int, Self],
    ) -> dict[int, Self]:
        """Ensures the results are in the same order as requested and prints a warning if some results are missing."""
        results = {entity_id: results[entity_id] for entity_id in ids_requested if entity_id in results}
        if len(results) != len(ids_requested):
            logger.warning(f"Only found {len(results)} out of {len(ids_requested)}.")
        return results
