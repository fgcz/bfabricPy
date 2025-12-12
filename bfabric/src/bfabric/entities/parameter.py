from __future__ import annotations

from bfabric.entities.core.entity import Entity


class Parameter(Entity):
    ENDPOINT = "parameter"

    @property
    def key(self) -> str:
        key = self["key"]
        if not isinstance(key, str):
            raise TypeError("key is not a string")
        return key

    @property
    def value(self) -> str | None:
        try:
            value = self["value"]
        except KeyError:
            # in principle, this should only be possible when "Required" = false
            return None
        if not isinstance(value, str):
            raise TypeError("value is not a string")
        return value
