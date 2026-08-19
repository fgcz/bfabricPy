from __future__ import annotations

import datetime
import importlib.metadata
import warnings
from typing import TYPE_CHECKING, Any, Literal, Self, cast

from pydantic import BaseModel, model_validator

from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from bfabric.typing import ApiResponseObjectType


class EntityDump(BaseModel):
    """The on-disk form of a single entity: its API data plus the provenance needed to reload it.

    ``uri`` is the point of the envelope, as it records the B-Fabric instance, entity type and id the ``data`` came
    from — none of which the payload alone identifies, since ids are only unique within one instance.
    """

    format_version: Literal[1] = 1
    uri: EntityUri
    dumped_at: datetime.datetime
    bfabricpy_version: str
    data: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    """The entity's data dictionary, verbatim and unvalidated."""

    @classmethod
    def create(cls, uri: EntityUri, data: ApiResponseObjectType) -> Self:
        """Builds a dump of ``data``, stamped with the current time and bfabricPy version."""
        return cls(
            uri=uri,
            dumped_at=datetime.datetime.now(datetime.UTC),
            bfabricpy_version=importlib.metadata.version("bfabric"),
            data=dict(data),
        )

    @model_validator(mode="after")
    def _check_data_matches_uri(self) -> Self:
        components = self.uri.components
        for field, expected in (("id", components.entity_id), ("classname", components.entity_type)):
            actual = self.data.get(field)
            if actual != expected:
                msg = f"data[{field!r}] is {actual!r}, but the URI says {expected!r}: {self.uri}"
                raise ValueError(msg)
        return self


def parse_document(document: object, bfabric_instance: str | None) -> tuple[ApiResponseObjectType, str | None]:
    """Extracts the data dictionary and its B-Fabric instance from a parsed entity YAML document.

    Files written before the provenance metadata existed are bare data dictionaries; those are still accepted, with
    a warning, and fall back to the passed ``bfabric_instance``.

    :raises ValueError: if the document is not a mapping, or was dumped from another B-Fabric instance than the one
        requested
    """
    if not isinstance(document, dict):
        msg = f"Expected a mapping at the top level of the entity file, found {type(document).__name__}"
        raise ValueError(msg)
    document = cast("ApiResponseObjectType", document)

    if "format_version" not in document:
        warnings.warn(
            "Entity files without a 'format_version' are deprecated; dump the entity again to record its URI.",
            DeprecationWarning,
            stacklevel=3,
        )
        return document, bfabric_instance

    dump = EntityDump.model_validate(document)
    dumped_instance = str(dump.uri.components.bfabric_instance)
    if bfabric_instance is not None and bfabric_instance.rstrip("/") != dumped_instance.rstrip("/"):
        msg = f"Entity was dumped from {dumped_instance}, which is not the requested instance {bfabric_instance}"
        raise ValueError(msg)
    return dump.data, dumped_instance
