from __future__ import annotations

import re
import urllib.parse
from collections import defaultdict
from typing import TYPE_CHECKING, Annotated, Any

import annotated_types
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
)
from pydantic_core import core_schema

if TYPE_CHECKING:
    from collections.abc import Iterator

_URI_REGEX = re.compile(
    r"^(?P<bfabric_instance>(https://[^/]+/bfabric/|http://localhost(:\d+)?/bfabric/))(?P<entity_type>\w+)/show\.html\?id=(?P<entity_id>\d+)$"
)


def _validate_entity_uri(uri: str) -> str:
    _ = _parse_uri_components(uri)
    return uri


def _parse_uri_components(uri: str) -> EntityUriComponents:
    match = _URI_REGEX.match(uri)
    if not match:
        raise ValueError(f"Invalid Entity URI: {uri}")
    return EntityUriComponents.model_validate(match.groupdict())


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
        return EntityUriComponents(
            bfabric_instance=bfabric_instance, entity_type=entity_type, entity_id=entity_id
        ).as_uri()

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
    entity_id: Annotated[int, annotated_types.Gt(0)]

    def as_uri(self) -> EntityUri:
        uri = urllib.parse.urljoin(f"{self.bfabric_instance}/", f"{self.entity_type}/show.html?id={self.entity_id}")
        return EntityUri(uri)


class GroupedUris(BaseModel):
    class GroupKey(BaseModel):
        model_config = ConfigDict(frozen=True)
        bfabric_instance: str
        entity_type: str

    groups: dict[GroupKey, list[EntityUri]] = {}

    def items(self) -> Iterator[tuple[GroupKey, list[EntityUri]]]:
        yield from self.groups.items()

    @classmethod
    def from_uris(cls, uris: list[EntityUri]) -> GroupedUris:
        groups = defaultdict(list)
        for uri in uris:
            key = cls.GroupKey(
                bfabric_instance=str(uri.components.bfabric_instance), entity_type=uri.components.entity_type
            )
            groups[key].append(uri)
        return cls(groups=dict(groups))
