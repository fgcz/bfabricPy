from __future__ import annotations

from typing import Any, TYPE_CHECKING

from loguru import logger
from pydantic import BaseModel

from bfabric.entities.core.import_entity import instantiate_entity
from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from bfabric import Bfabric


class _ReferenceInformation(BaseModel):
    name: str
    uris: list[EntityUri]
    is_singular: bool
    is_loaded: bool


class References:
    def __init__(self, client: Bfabric, bfabric_instance: str, data_ref: dict[str, Any]) -> None:
        self._client = client
        self._bfabric_instance = bfabric_instance
        self._data_ref = data_ref

        # Retrieve information about all reference fields
        self._ref_info = self.__extract_reference_info(data_ref=data_ref, bfabric_instance=self._bfabric_instance)

        self._cache = {}

    @property
    def uris(self) -> dict[str, EntityUri | list[EntityUri]]:
        """Returns a shallow copy of the reference URIs dictionary."""
        return {info.name: (info.uris[0] if info.is_singular else info.uris) for info in self._ref_info.values()}

    def is_loaded(self, name: str) -> bool:
        """Returns whether the reference with the given name is already loaded.
        :raises KeyError: If the reference with the given name does not exist.
        """
        return self._ref_info[name].is_loaded

    def get(self, name: str) -> Any | None:
        if name in self._cache:
            return self._cache[name]

        ref_info = self._ref_info.get(name)
        if ref_info is None:
            return None
        if not ref_info.is_loaded:
            self.__load(ref_info=ref_info)

        data_dicts = [self._data_ref[name]] if ref_info.is_singular else self._data_ref[name]
        entities = [
            instantiate_entity(data_dict=data_dict, client=self._client, bfabric_instance=self._bfabric_instance)
            for data_dict in data_dicts
        ]
        if ref_info.is_singular:
            self._cache[name] = entities[0]
        else:
            self._cache[name] = entities
        return self._cache[name]

    def __getattr__(self, name: str) -> Any:
        value = self.get(name)
        if value is None:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return value

    def __contains__(self, name: str) -> bool:
        return name in self._ref_info

    def __load(self, ref_info: _ReferenceInformation) -> None:
        from bfabric.entities.core.entity_reader import EntityReader

        reader = EntityReader(self._client)
        entities = reader.read_uris(ref_info.uris)

        # merge into the ref_data object
        if ref_info.is_singular:
            self._data_ref[ref_info.name].update(entities[ref_info.uris[0]].data_dict)
        else:
            # TODO does this need some more testing?
            indices_map = {uri: idx for idx, uri in enumerate(ref_info.uris)}
            for entry_uri in self._data_ref[ref_info.name].uris:
                self._data_ref[ref_info.name][indices_map[entry_uri]].update(entities[entry_uri].data_dict)

        # mark as loaded
        ref_info.is_loaded = True

    @classmethod
    def __extract_reference_info(
        cls, data_ref: dict[str, Any], bfabric_instance: str
    ) -> dict[str, _ReferenceInformation]:
        references = {}
        for name, value in data_ref.items():
            refs = cls.__extract_reference_info_item(name, value, bfabric_instance)
            if refs is not None:
                references[name] = refs
        return dict(references)

    @classmethod
    def __extract_reference_info_item(
        cls, name: str, value: Any, bfabric_instance: str
    ) -> _ReferenceInformation | None:
        if isinstance(value, dict) and "classname" in value and "id" in value:
            info = cls.__extract_reference_info_item_dict(value, bfabric_instance)
            return _ReferenceInformation(name=name, uris=[info["uri"]], is_singular=True, is_loaded=info["is_loaded"])

        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            try:
                refs = [cls.__extract_reference_info_item_dict(item, bfabric_instance) for item in value]
            except KeyError:
                logger.warning(f"Reference list '{name}' contains invalid items, skipping.")
                return None

            uris = [ref["uri"] for ref in refs]
            is_loaded = all(ref["is_loaded"] for ref in refs)
            return _ReferenceInformation(name=name, uris=uris, is_singular=False, is_loaded=is_loaded)

    @classmethod
    def __extract_reference_info_item_dict(
        cls, value: dict[str, Any], bfabric_instance: str
    ) -> dict[str, EntityUri | bool]:
        uri = EntityUri.from_components(bfabric_instance, value["classname"], value["id"])
        # TODO double check if this handles the more complex references
        is_loaded = len(value) > 2
        return {"uri": uri, "is_loaded": is_loaded}
