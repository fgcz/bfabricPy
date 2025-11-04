from __future__ import annotations

import warnings
from functools import cached_property
from typing import TYPE_CHECKING

import yaml

from bfabric.entities.core.find_mixin import FindMixin
from bfabric.entities.core.references import References
from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric import Bfabric
    from typing import Any, Self


class Entity(FindMixin):
    def __init__(
        self,
        data_dict: dict[str, Any],
        client: Bfabric | None,
        bfabric_instance: str,
    ) -> None:
        self._data_dict = data_dict
        self.__client = client
        self.__bfabric_instance = bfabric_instance

    @property
    def bfabric_instance(self) -> str:
        """The bfabric instance URL associated with the entity."""
        return self.__bfabric_instance

    @property
    def classname(self) -> str:
        """The entity's classname."""
        return self._data_dict["classname"]

    @property
    def id(self) -> int:
        """The entity's ID."""
        return int(self._data_dict["id"])

    @property
    def uri(self) -> EntityUri:
        """The entity's URI."""
        return EntityUri.from_components(
            bfabric_instance=self.bfabric_instance, entity_type=self.classname, entity_id=self.id
        )

    @cached_property
    def refs(self) -> References:
        return References(client=self._client, data_ref=self._data_dict)

    @property
    def data_dict(self) -> dict[str, Any]:
        """Returns a shallow copy of the entity's data dictionary."""
        return self._data_dict.copy()

    @property
    def _client(self) -> Bfabric | None:
        """Returns the client associated with the entity."""
        return self.__client

    # @property
    # def ENDPOINT(self) -> str:
    #    # TODO deprecate and delete
    #    warnings.warn("Entity.ENDPOINT is deprecated, use Entity.classname instead.", DeprecationWarning, stacklevel=2)
    #    return self.classname

    @property
    def web_url(self) -> str:
        # TODO deprecate and delete
        warnings.warn("Entity.web_url is deprecated, use str(Entity.uri) instead.", DeprecationWarning, stacklevel=2)
        return str(self.uri)

    def __lt__(self, other: Entity) -> bool:
        """Compares the entity with another entity based on their IDs."""
        if self.classname != other.classname:
            return NotImplemented
        return self.id < other.id


class LegacyEntity(Entity, FindMixin):
    def __init__(
        self, data_dict: dict[str, Any], client: Bfabric | None, *, bfabric_instance: str | None = None
    ) -> None:
        self.__data_dict = data_dict
        self.__client = client
        self.__bfabric_instance = bfabric_instance

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

    def __repr__(self) -> str:
        """Returns the string representation of the workunit."""
        return f"{self.__class__.__name__}({repr(self.__data_dict)}, client={repr(self.__client)})"

    __str__ = __repr__
