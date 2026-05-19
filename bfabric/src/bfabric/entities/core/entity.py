# pyright: reportImportCycles=false

from __future__ import annotations

import warnings
from functools import cached_property
from typing import TYPE_CHECKING, Self, TypeGuard

from bfabric.entities.core.mixins.find_mixin import FindMixin
from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from bfabric import Bfabric
    from bfabric.entities.core.references import References
    from bfabric.typing import ApiResponseDataType, ApiResponseObjectType


class Entity(FindMixin):
    """A single generic entity, read from B-Fabric."""

    def __init__(
        self,
        data_dict: ApiResponseObjectType,
        client: Bfabric | None = None,
        bfabric_instance: str | None = None,
    ) -> None:
        # note: client may be removed completely in the future,
        #       as I think it is a design mistake to have put them into these classes
        #       we rather need a registry of authenticated clients for different bfabric instances, to allow web apps
        #       serve multiple bfabric instances simultaneously.
        if bfabric_instance is None:
            warnings.warn(
                "In the future, creating an Entity object without bfabric_instance will not be supported.",
                DeprecationWarning,
            )
            bfabric_instance = client.config.base_url if client is not None else None

        self.__data_dict = data_dict
        self.__client = client
        self.__bfabric_instance = bfabric_instance

    @property
    def id(self) -> int:
        """Returns the entity's ID."""
        value = self.__data_dict["id"]
        if not isinstance(value, int):
            raise ValueError("Invalid ID")
        return value

    @property
    def bfabric_instance(self) -> str:
        """The bfabric instance URL associated with the entity."""
        return self.__bfabric_instance

    @property
    def classname(self) -> str:
        """The entity's classname."""
        value = self.__data_dict["classname"]
        if not isinstance(value, str):
            raise ValueError("Invalid classname")
        return value

    def ENDPOINT(self) -> str:  # noqa
        warnings.warn("Entity.ENDPOINT is deprecated, use Entity.classname instead.", DeprecationWarning, stacklevel=2)
        return self.classname

    @property
    def uri(self) -> EntityUri:
        """The entity's URI."""
        return EntityUri.from_components(
            bfabric_instance=self.__bfabric_instance, entity_type=self.classname, entity_id=self.id
        )

    @property
    def web_url(self) -> str:
        # TODO deprecate and delete
        warnings.warn("Entity.web_url is deprecated, use str(Entity.uri) instead.", DeprecationWarning, stacklevel=2)
        return str(self.uri)

    @property
    def data_dict(self) -> ApiResponseObjectType:
        """Returns a shallow copy of the entity's data dictionary."""
        return self.__data_dict.copy()

    @cached_property
    def refs(self) -> References:
        """Returns the entity's references manager."""
        from bfabric.entities.core.references import References

        return References(client=self._client, bfabric_instance=self.__bfabric_instance, data_ref=self.__data_dict)

    @property
    def custom_attributes(self) -> dict[str, str]:
        """Returns custom attributes as a dictionary, if the entity has any.

        If the field exists but is empty, an empty dictionary is returned.
        If the field does not exist, an `AttributeError` is raised.
        """
        if "customattribute" not in self.__data_dict:
            msg = f"Entity of classname '{self.classname}' has no custom attributes."
            raise AttributeError(msg)

        custom_attributes_list = self.__data_dict["customattribute"]
        if not _is_custom_attributes_list(custom_attributes_list):
            raise ValueError("invalid type for customattribute")

        return {attr["name"]: attr["value"] for attr in custom_attributes_list}

    @property
    def _client(self) -> Bfabric | None:
        """Returns the client associated with the entity."""
        return self.__client

    def __contains__(self, key: str) -> bool:
        """Checks if a key is present in the data dictionary."""
        return key in self.__data_dict

    def __getitem__(self, key: str) -> ApiResponseDataType:
        """Returns the value of a key in the data dictionary."""
        return self.__data_dict[key]

    def get(self, key: str, default: Any = None) -> ApiResponseDataType | None:
        """Returns the value of a key in the data dictionary, or a default value if the key is not present."""
        return self.__data_dict.get(key, default)

    def __lt__(self, other: Entity) -> bool:
        """Compares the entity with another entity based on their IDs."""
        if self.classname != other.classname:
            return NotImplemented
        return self.id < other.id

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(data_dict={self.__data_dict!r}, bfabric_instance={self.__bfabric_instance!r})"
        )

    __str__ = __repr__

    def dump_yaml(self, path: Path) -> None:
        """Writes the entity's data dictionary to a YAML file."""
        # TODO (#351): to be extended
        import yaml

        with path.open("w") as file:
            yaml.safe_dump(self.__data_dict, file)

    @classmethod
    def load_yaml(cls, path: Path, client: Bfabric | None = None, bfabric_instance: str | None = None) -> Self:
        """Loads an entity from a YAML file."""
        # TODO (#351): to be extended
        import yaml

        with path.open("r") as file:
            data = yaml.safe_load(file)
        return cls(data, client=client, bfabric_instance=bfabric_instance)


def _is_custom_attributes_list(custom_attributes: ApiResponseDataType) -> TypeGuard[list[dict[str, str]]]:
    if not isinstance(custom_attributes, list):
        return False
    for item in custom_attributes:
        if not isinstance(item, dict) or any(not isinstance(value, str) for value in item.values()):
            return False
    return True
