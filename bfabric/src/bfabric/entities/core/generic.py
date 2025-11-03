from functools import cached_property
from typing import Any

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.uri import EntityUri


class GenericEntity(Entity):
    def __init__(self, data_dict: dict[str, Any], client: Any | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    @cached_property
    def references(self) -> dict[str, EntityUri]:
        references = {}
        for key, value in self.data_dict.items():
            refs = self._extract_reference_dict(value)
            if refs:
                references[key] = refs
        return dict(references)

    @cached_property
    def attributes(self) -> dict[str, Any]:
        attrs = {}
        for key, value in self.data_dict.items():
            if key not in self.references:
                attrs[key] = value
        return attrs

    def _extract_reference_dict(self, value: Any) -> Any:
        if isinstance(value, dict) and "classname" in value and "id" in value:
            return EntityUri.from_components(self._client.config.base_url, value["classname"], value["id"])
        if isinstance(value, list):
            refs = [self._extract_reference_dict(item) for item in value]
            return [ref for ref in refs if ref is not None]
