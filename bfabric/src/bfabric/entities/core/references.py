from __future__ import annotations

from typing import Any, TYPE_CHECKING

from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity


class References:
    def __init__(self, entity: Entity) -> None:
        self._entity = entity
        self._parsed = self.__parse_references(entity)
        # TODO instead of creating a separate field,
        #      we should store it in the same, in the same way as it will be returned when "fulldetails" is used
        #      -> that will allow us to support fulldetails responses transparently in the future
        self._loaded = {}

    @property
    def dict(self) -> dict[str, EntityUri | list[EntityUri]]:
        return self._parsed.copy()

    def get(self, name: str) -> Any | None:
        if name not in self._loaded and name in self._parsed:
            self.__load(name)
        if name in self._loaded:
            return self._loaded[name]

    def __getattr__(self, name: str) -> Any:
        value = self.get(name)
        if value is None:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return value

    def __contains__(self, name: str) -> bool:
        return name in self._parsed

    def __repr__(self) -> str:
        return f"References({sorted(self._parsed.keys())})"

    def __load(self, name: str) -> None:
        from bfabric.entities.core.entity_reader import EntityReader

        reader = EntityReader(self._entity._client)
        if isinstance(self._parsed[name], list):
            self._loaded[name] = list(reader.read_uris(uris=self._parsed[name]).values())
        else:
            self._loaded[name] = reader.read_uri(self._parsed[name])

    @classmethod
    def __parse_references(cls, entity: Entity) -> dict[str, EntityUri | list[EntityUri]]:
        references = {}
        for key, value in entity.data_dict.items():
            refs = cls.__extract_reference_dict(value, entity.bfabric_instance)
            if refs:
                references[key] = refs
        return dict(references)

    @classmethod
    def __extract_reference_dict(cls, value: Any, bfabric_instance: str) -> EntityUri | list[EntityUri] | None:
        if isinstance(value, dict) and "classname" in value and "id" in value:
            return EntityUri.from_components(bfabric_instance, value["classname"], value["id"])
        if isinstance(value, list):
            refs = [cls.__extract_reference_dict(item, bfabric_instance) for item in value]
            return [ref for ref in refs if ref is not None]
