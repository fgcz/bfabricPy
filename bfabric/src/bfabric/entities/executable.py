from __future__ import annotations

import base64
import warnings
from functools import cached_property
from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric.entities import Parameter


class Executable(Entity):
    ENDPOINT = "executable"

    storage = HasOne(bfabric_field="storage", optional=True)
    parameters: HasMany[Parameter] = HasMany(bfabric_field="parameter", optional=True)

    @cached_property
    def decoded_bytes(self) -> bytes | None:
        if "base64" not in self:
            return None
        base64_value = self["base64"]
        if not isinstance(base64_value, str):
            raise ValueError("base64 value must be a string")
        return base64.decodebytes(base64_value.encode("utf-8"))

    @property
    def decoded_str(self) -> str | None:
        if self.decoded_bytes is not None:
            return self.decoded_bytes.decode("utf-8")
        return None

    @property
    def decoded(self) -> str | None:
        # TODO deprecation
        warnings.warn(
            "The 'decoded' property is deprecated and will be removed in a future version. Use decoded_str instead.",
            DeprecationWarning,
        )
        return self.decoded_str
