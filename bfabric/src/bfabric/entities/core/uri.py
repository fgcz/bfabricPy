from __future__ import annotations

import urllib.parse
from collections import defaultdict
from typing import TYPE_CHECKING, Annotated, Any

import annotated_types
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    StringConstraints,
    TypeAdapter,
)
from pydantic_core import core_schema

from bfabric.config.base_url import BaseUrl

if TYPE_CHECKING:
    from collections.abc import Iterator

_NORMALIZE_HINT = "use EntityUri.normalize to accept a browser URL"


def _validate_entity_uri(uri: str) -> str:
    _ = _parse_uri_components(uri)
    return uri


def _parse_uri_components(uri: str, *, allow_extra_query: bool = False) -> EntityUriComponents:
    """Parse a B-Fabric entity URI into its components.

    :param uri: the URI to parse
    :param allow_extra_query: ignore query parameters other than ``id``, and any fragment, instead of
        rejecting them (i.e. accept a URL as copied from the browser)
    :raises ValueError: if the URI is not a valid entity URI
    """

    def invalid(reason: str) -> ValueError:
        return ValueError(f"Invalid Entity URI: {uri} ({reason})")

    parsed = urllib.parse.urlsplit(uri)
    host = (parsed.hostname or "").lower()
    if not host or (parsed.scheme != "https" and (parsed.scheme, host) != ("http", "localhost")):
        raise invalid("expected https://<instance> or http://localhost")
    if parsed.username or parsed.password:
        raise invalid("credentials are not allowed")

    segments = parsed.path.split("/")[1:]
    if len(segments) != 3 or segments[0] != "bfabric" or segments[2] != "show.html":
        raise invalid("expected path /bfabric/<entity_type>/show.html")

    entity_ids = set(urllib.parse.parse_qs(parsed.query).get("id", []))
    if len(entity_ids) != 1:
        raise invalid("conflicting 'id' query parameters" if entity_ids else "missing 'id' query parameter")
    entity_id = entity_ids.pop()
    if not entity_id.isdigit():
        raise invalid("entity id must be a positive integer")
    # Strict mode parses the same way, then insists the URI was canonical to begin with.
    if not allow_extra_query and (parsed.query != f"id={entity_id}" or parsed.fragment):
        raise invalid(f"expected query exactly 'id=<entity_id>' and no fragment; {_NORMALIZE_HINT}")

    return EntityUriComponents(
        bfabric_instance=BaseUrl(f"{parsed.scheme}://{parsed.netloc.lower()}/bfabric"),
        entity_type=segments[1],
        entity_id=int(entity_id),
    )


ValidatedEntityUri = Annotated[str, AfterValidator(_validate_entity_uri)]
entity_uri_adapter: TypeAdapter[str] = TypeAdapter(ValidatedEntityUri)


class EntityUri(str):
    """B-Fabric entity URI with validation and component parsing.

    URIs follow the pattern: ``https://instance/bfabric/{entity_type}/show.html?id={id}``

    Example:
        >>> uri = EntityUri("https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123")
        >>> uri.components.entity_type
        'sample'
        >>> uri.components.entity_id
        123
    """

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
    def from_components(cls, bfabric_instance: BaseUrl, entity_type: str, entity_id: int) -> EntityUri:
        """Create EntityUri from individual components.

        Args:
            bfabric_instance: B-Fabric instance URL (e.g., "https://fgcz-bfabric.uzh.ch/bfabric")
            entity_type: Entity type name (e.g., "sample", "project")
            entity_id: Numeric ID of the entity

        Returns:
            Validated EntityUri string
        """
        return EntityUriComponents(
            bfabric_instance=bfabric_instance, entity_type=entity_type, entity_id=entity_id
        ).as_uri()

    @classmethod
    def normalize(cls, url: str) -> EntityUri:
        """Normalize a B-Fabric web URL, e.g. one copied from the browser, to a canonical EntityUri.

        Extra query parameters and the fragment are dropped, so unlike the constructor this accepts
        ``.../show.html?id=123&tab=details``, returning the canonical URI of the referenced entity.
        """
        return _parse_uri_components(url, allow_extra_query=True).as_uri()

    @property
    def components(self) -> EntityUriComponents:
        """Access parsed URI components."""
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
    """Parsed components of an EntityUri.

    Attributes:
        bfabric_instance: B-Fabric instance URL
        entity_type: Entity type name (lowercase letters only)
        entity_id: Numeric entity ID (must be positive)
    """

    bfabric_instance: BaseUrl
    entity_type: Annotated[str, StringConstraints(pattern=r"^[a-z]+$")]
    entity_id: Annotated[int, annotated_types.Gt(0)]

    def as_uri(self) -> EntityUri:
        """Convert components back to EntityUri string."""
        uri = urllib.parse.urljoin(f"{self.bfabric_instance}/", f"{self.entity_type}/show.html?id={self.entity_id}")
        return EntityUri(uri)


class GroupedUris(BaseModel):
    """Groups EntityUris by B-Fabric instance and entity type for batch processing.

    Used internally by EntityReader to batch API calls efficiently.
    """

    class GroupKey(BaseModel):
        """Grouping key for EntityUris."""

        model_config = ConfigDict(frozen=True)
        bfabric_instance: BaseUrl
        entity_type: str

    groups: dict[GroupKey, list[EntityUri]] = {}

    def items(self) -> Iterator[tuple[GroupKey, list[EntityUri]]]:
        """Iterate over grouped URIs."""
        yield from self.groups.items()

    @classmethod
    def from_uris(cls, uris: list[EntityUri]) -> GroupedUris:
        """Create GroupedUris from a list of EntityUris.

        Args:
            uris: List of EntityUri objects to group

        Returns:
            GroupedUris with URIs grouped by instance and type
        """
        groups = defaultdict(list)
        for uri in uris:
            key = cls.GroupKey(bfabric_instance=uri.components.bfabric_instance, entity_type=uri.components.entity_type)
            groups[key].append(uri)
        return cls(groups=dict(groups))
