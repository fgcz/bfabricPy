from __future__ import annotations

import math
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

# Single page query limit for BFabric API (as of time of writing, adapt if it changes)
BFABRIC_QUERY_LIMIT = 100

T = TypeVar("T")


def page_iter(objs: Sequence[T], page_size: int = BFABRIC_QUERY_LIMIT) -> Generator[list[T], None, None]:
    """Yields `objs` in chunks of at most `page_size`, i.e. one chunk per B-Fabric query."""
    for i in range(0, len(objs), page_size):
        yield list(objs[i : i + page_size])


def compute_requested_pages(
    n_page_total: int,
    n_item_per_page: int,
    n_item_offset: int,
    n_item_return_max: int | None,
) -> tuple[list[int], int]:
    """Returns the page indices that need to be requested to get all requested items.
    :param n_page_total: Total number of pages available
    :param n_item_per_page: Number of items per page
    :param n_item_offset: Number of items to skip from the beginning
    :param n_item_return_max: Maximum number of items to return
    :return:
        - list of page indices that need to be requested
        - initial page offset (0-based), i.e. the i-th item from which onwards to retain results
    """
    # B-Fabric API uses 1-based indexing for pages
    index_start = 1

    # Determine the page indices to request
    # If n_item_return_max is not provided, we will return all items
    if n_item_return_max is None:
        n_item_return_max = n_page_total * n_item_per_page

    # Determine the page indices to request
    idx_max_return = math.ceil((n_item_return_max + n_item_offset) / n_item_per_page)
    idx_arr = [idx + index_start for idx in range(n_item_offset // n_item_per_page, min(n_page_total, idx_max_return))]

    # Determine the initial offset on the first page
    initial_offset = min(n_item_offset, n_item_return_max) % n_item_per_page

    return idx_arr, initial_offset
