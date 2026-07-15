from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

from loguru import logger

from bfabric.entities.core.reader_utils import entities_by_id

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from bfabric import Bfabric
    from bfabric.typing import ApiRequestObjectType


class _HasEndpoint(Protocol):
    ENDPOINT: str


T = TypeVar("T", bound=_HasEndpoint)


class FindMixin:
    @classmethod
    def find(cls: type[T], id: int, client: Bfabric) -> T | None:
        """Finds an entity by its ID, if it does not exist `None` is returned."""
        from bfabric.entities.core.entity_reader import EntityReader

        warnings.warn(
            "FindMixin is deprecated and will be removed in future versions.", DeprecationWarning, stacklevel=2
        )
        return EntityReader.for_client(client=client).read_id(entity_type=cls.ENDPOINT, entity_id=id)

    @classmethod
    def find_all(cls: type[T], ids: Sequence[int | str], client: Bfabric) -> dict[int, T]:
        """Returns a dictionary of entities with the given IDs. The order will generally match the input, however,
        if some entities are not found they will be omitted and a warning will be logged.
        """
        from bfabric.entities.core.entity_reader import EntityReader

        warnings.warn(
            "FindMixin is deprecated and will be removed in future versions.", DeprecationWarning, stacklevel=2
        )
        results = EntityReader.for_client(client=client).read_ids(cls.ENDPOINT, list(ids))
        # ``entities_by_id`` is typed for ``Entity`` values, whereas ``FindMixin.T`` is the deprecated
        # protocol-bound typevar; the runtime dict is correct, so bridge the two with a cast.
        return _ensure_results_order(ids, cast("dict[int, T]", entities_by_id(results)))

    @classmethod
    def find_by(
        cls: type[T], obj: ApiRequestObjectType, client: Bfabric, max_results: int | None = 100
    ) -> dict[int, T]:
        """Returns a dictionary of entities that match the given query."""
        from bfabric.entities.core.entity_reader import EntityReader

        warnings.warn(
            "FindMixin is deprecated and will be removed in future versions.", DeprecationWarning, stacklevel=2
        )
        reader = EntityReader.for_client(client=client)
        bfabric_instance = client.config.base_url
        results = reader.query(
            entity_type=cls.ENDPOINT, obj=obj, bfabric_instance=bfabric_instance, max_results=max_results
        )
        return cast("dict[int, T]", entities_by_id(results))


def _ensure_results_order(
    ids_requested: Sequence[int | str],
    results: Mapping[int, T],
) -> dict[int, T]:
    """Ensures the results are in the same order as requested and prints a warning if some results are missing."""
    results = {int(entity_id): results[int(entity_id)] for entity_id in ids_requested if int(entity_id) in results}
    if len(results) != len(ids_requested):
        logger.warning(f"Only found {len(results)} out of {len(ids_requested)}.")
    return results
