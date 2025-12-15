# pyright: reportImportCycles=false

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from loguru import logger
from pydantic import BaseModel

from bfabric.entities.core.import_entity import instantiate_entity
from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.core.entity import Entity
    from bfabric.typing import ApiResponseDataType, ApiResponseObjectType


class _ReferenceInformation(BaseModel):
    name: str
    uris: list[EntityUri]
    is_singular: bool
    is_loaded: bool


class References:
    """References manager for a B-Fabric entity.

    References can be loaded, in which case their full data is available at the expected field in the data dictionary,
    or, they can be unloaded, in which case only a reference (classname and id) is present.

    This is compatible with pre-loaded references from B-Fabric API (i.e. fulldetails).

    This class receives a reference to the entity's data dictionary, updating it in-place when references are loaded.
    """

    def __init__(self, client: Bfabric, bfabric_instance: str, data_ref: ApiResponseObjectType) -> None:
        self._client: Bfabric = client
        self._bfabric_instance: str = bfabric_instance
        self._data_ref: ApiResponseObjectType = data_ref

        # Retrieve information about all reference fields
        self._ref_info: dict[str, _ReferenceInformation] = self.__extract_reference_info(
            data_ref=data_ref, bfabric_instance=self._bfabric_instance
        )
        self._cache: dict[str, Entity | list[Entity]] = {}

    @property
    def uris(self) -> dict[str, EntityUri | list[EntityUri]]:
        """Returns a shallow copy of the reference URIs dictionary."""
        return {info.name: (info.uris[0] if info.is_singular else info.uris) for info in self._ref_info.values()}

    def is_loaded(self, name: str) -> bool:
        """Returns whether the reference with the given name is already loaded.
        :raises KeyError: If the reference with the given name does not exist.
        """
        return self._ref_info[name].is_loaded

    def get(self, name: str) -> Entity | list[Entity] | None:
        if name in self._cache:
            return self._cache[name]

        ref_info = self._ref_info.get(name)
        if ref_info is None:
            return None
        if not ref_info.is_loaded:
            self.__load(ref_info=ref_info)

        data_dicts = self.__get_ref_data_dicts(name, ref_info.is_singular)
        entities = [
            instantiate_entity(data_dict=data_dict, client=self._client, bfabric_instance=self._bfabric_instance)
            for data_dict in data_dicts
        ]

        self._cache[name] = entities[0] if ref_info.is_singular else entities
        return self._cache[name]

    def __getattr__(self, name: str) -> Entity | list[Entity]:
        value = self.get(name)
        if value is None:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return value

    def __contains__(self, name: str) -> bool:
        return name in self._ref_info

    def __get_ref_data_dicts(self, name: str, is_singular: bool) -> list[dict[str, ApiResponseDataType]]:
        """Extract reference data as a list of dicts, using is_singular to determine the expected structure."""
        raw_data = self._data_ref[name]
        if is_singular:
            # is_singular=True means raw_data should be a dict
            return [cast("dict[str, ApiResponseDataType]", raw_data)]
        else:
            # is_singular=False means raw_data should be a list of dicts
            return cast("list[dict[str, ApiResponseDataType]]", raw_data)

    def __update_ref_data(self, ref_info: _ReferenceInformation, entities: dict[EntityUri, Entity | None]) -> None:
        """Update reference data in-place with loaded entity data, handling None entities."""
        if ref_info.is_singular:
            ref_data = cast("dict[str, ApiResponseDataType]", self._data_ref[ref_info.name])
            entity = entities[ref_info.uris[0]]
            if entity is None:
                raise ValueError(f"Entity not found for URI: {ref_info.uris[0]}")
            ref_data.update(entity.data_dict)
        else:
            ref_data_list = cast("list[dict[str, ApiResponseDataType]]", self._data_ref[ref_info.name])
            indices_map = {uri: idx for idx, uri in enumerate(ref_info.uris)}
            for entry_uri in ref_info.uris:
                entity = entities[entry_uri]
                if entity is None:
                    raise ValueError(f"Entity not found for URI: {entry_uri}")
                ref_data_list[indices_map[entry_uri]].update(entity.data_dict)

    def __load(self, ref_info: _ReferenceInformation) -> None:
        from bfabric.entities.core.entity_reader import EntityReader

        reader = EntityReader.for_client(self._client)
        entities = reader.read_uris(ref_info.uris)

        self.__update_ref_data(ref_info, entities)
        ref_info.is_loaded = True

    @classmethod
    def __extract_reference_info(
        cls, data_ref: ApiResponseObjectType, bfabric_instance: str
    ) -> dict[str, _ReferenceInformation]:
        references: dict[str, _ReferenceInformation] = {}
        for name, value in data_ref.items():
            refs = cls.__extract_reference_info_item(name, value, bfabric_instance)
            if refs is not None:
                references[name] = refs
        return dict(references)

    @classmethod
    def __extract_reference_info_item(
        cls, name: str, value: ApiResponseDataType, bfabric_instance: str
    ) -> _ReferenceInformation | None:
        if isinstance(value, dict) and "classname" in value and "id" in value:
            info = cls.__extract_reference_info_item_dict(value, bfabric_instance)
            return _ReferenceInformation.model_validate(
                dict(name=name, uris=[info["uri"]], is_singular=True, is_loaded=info["is_loaded"])
            )

        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            try:
                refs = [cls.__extract_reference_info_item_dict(item, bfabric_instance) for item in value]
            except KeyError:
                logger.warning(f"Reference list '{name}' contains invalid items, skipping.")
                return None

            uris = [ref["uri"] for ref in refs]
            is_loaded = all(ref["is_loaded"] for ref in refs)
            return _ReferenceInformation.model_validate(
                dict(name=name, uris=uris, is_singular=False, is_loaded=is_loaded)
            )

    @classmethod
    def __extract_reference_info_item_dict(
        cls, value: ApiResponseDataType, bfabric_instance: str
    ) -> dict[str, EntityUri | bool]:
        # value is guaranteed to be a dict by the caller's isinstance check
        value_dict = cast("dict[str, ApiResponseDataType]", value)
        classname = cast("str", value_dict["classname"])
        entity_id = cast("int", value_dict["id"])

        uri = EntityUri.from_components(bfabric_instance, classname, entity_id)
        # TODO double check if this handles the more complex references
        is_loaded = len(value_dict) > 2
        return {"uri": uri, "is_loaded": is_loaded}
