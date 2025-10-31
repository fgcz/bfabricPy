from __future__ import annotations
from typing import Annotated, Any
import urllib.parse
from pydantic import (
    HttpUrl,
    BaseModel,
    PositiveInt,
    StringConstraints,
    AfterValidator,
    TypeAdapter,
)
import re

from pydantic_core import core_schema

_URI_REGEX = re.compile(
    r"^(?P<bfabric_instance>https://[^/]+/bfabric/)(?P<entity_type>\w+)/show\.html\?id=(?P<entity_id>\d+)$"
)


def _validate_entity_uri(uri: str) -> str:
    if not _URI_REGEX.match(uri):
        raise ValueError(f"Invalid Entity URI: {uri}")
    return uri


ValidatedEntityUri = Annotated[str, AfterValidator(_validate_entity_uri)]
entity_uri_adapter: TypeAdapter[str] = TypeAdapter(ValidatedEntityUri)


class EntityUri(str):
    def __new__(cls, uri: str | EntityUri) -> EntityUri:
        if isinstance(uri, cls):
            return uri

        # Parse once for validation
        components = _parse_uri_components(uri)  # raises on invalid

        # Create instance
        instance = super().__new__(cls, uri)

        # Cache components using name mangling
        object.__setattr__(instance, "_EntityUri__components", components)
        return instance

    @classmethod
    def from_components(cls, bfabric_instance: str, entity_type: str, entity_id: int) -> EntityUri:
        uri = urllib.parse.urljoin(f"{bfabric_instance}/", f"{entity_type}/show.html?id={entity_id}")
        return cls(uri)

    @property
    def components(self) -> EntityUriComponents:
        # Access via name-mangled attribute
        return self.__components

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Any,
    ) -> core_schema.CoreSchema:
        """Provide Pydantic v2 schema for EntityUri."""
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )


class EntityUriComponents(BaseModel):
    bfabric_instance: HttpUrl
    entity_type: Annotated[str, StringConstraints(pattern=r"^[a-z]+$")]
    entity_id: PositiveInt

    def as_uri(self) -> EntityUri:
        uri = f"{self.bfabric_instance}{self.entity_type}/show.html?id={self.entity_id}"
        return EntityUri(uri)


def _parse_uri_components(uri: str) -> EntityUriComponents:
    match = _URI_REGEX.match(uri)
    if not match:
        raise ValueError(f"Invalid Entity URI: {uri}")
    return EntityUriComponents.model_validate(match.groupdict())
