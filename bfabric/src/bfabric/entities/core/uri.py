from __future__ import annotations
from functools import cached_property
from typing import Annotated

from pydantic import (
    HttpUrl,
    BaseModel,
    RootModel,
    model_validator,
    ConfigDict,
    PositiveInt,
    StringConstraints,
)
import re

_URI_REGEX = re.compile(
    r"^(?P<bfabric_instance>https://[^/]+/bfabric/)(?P<entity_type>\w+)/show\.html\?id=(?P<entity_id>\d+)$"
)


class EntityUri(RootModel):
    model_config = ConfigDict(frozen=True)
    root: str

    @cached_property
    def components(self) -> EntityUriComponents:
        return _parse_uri_components(self.root)

    @model_validator(mode="after")
    def _validate_uri(self) -> EntityUri:
        _ = self.components
        return self


class EntityUriComponents(BaseModel):
    bfabric_instance: HttpUrl
    entity_type: Annotated[str, StringConstraints(pattern=r"^[a-z]+$")]
    entity_id: PositiveInt

    def as_uri(self) -> EntityUri:
        uri = f"{self.bfabric_instance}{self.entity_type}/show.html?id={self.entity_id}"
        return EntityUri.model_validate(uri)


def _parse_uri_components(uri: str) -> EntityUriComponents:
    match = _URI_REGEX.match(uri)
    if not match:
        raise ValueError(f"Invalid Entity URI: {uri}")
    return EntityUriComponents.model_validate(match.groupdict())
