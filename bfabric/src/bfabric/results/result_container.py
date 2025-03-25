from __future__ import annotations

from typing import Any, TYPE_CHECKING, overload

from loguru import logger

import bfabric.results.response_format_dict as formatter

if TYPE_CHECKING:
    from collections.abc import Iterator
    import polars
    from bfabric.errors import BfabricRequestError


class ResultContainer:
    """Container structure for query results."""

    def __init__(
        self,
        results: list[dict[str, Any]],
        total_pages_api: int | None,
        errors: list[BfabricRequestError],
    ) -> None:
        """
        :param results:    List of BFabric query results
        :param total_pages_api:  Maximal number of pages that were available for reading.
            NOTE: User may have requested to cap the total number of results. Thus, it may be of interest to know
            the (approximate) total number of results the API had for the query. The total number of results is
            somewhere between max_pages * (BFABRIC_QUERY_LIMIT - 1) and max_pages * BFABRIC_QUERY_LIMIT
        :param errors:     List of errors that occurred during the query (if any)
        """
        self.results = results
        self._total_pages_api = total_pages_api
        self._errors = errors

    @overload
    def __getitem__(self, idx: int) -> dict[str, Any]: ...

    @overload
    def __getitem__(self, idx: slice) -> list[dict[str, Any]]: ...

    def __getitem__(self, idx: int | slice) -> dict[str, Any] | list[dict[str, Any]]:
        return self.results[idx]

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.results)

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return str(self.to_list_dict())

    def __len__(self) -> int:
        return len(self.results)

    def get_first_n_results(self, n_results: int | None) -> ResultContainer:
        """Returns a shallow copy of self, containing at most `n_results` results."""
        if n_results is None:
            return self
        else:
            return ResultContainer(
                self.results[:n_results],
                total_pages_api=self._total_pages_api,
                errors=self._errors,
            )

    def assert_success(self) -> None:
        """Asserts that the query was successful. Raises a `RuntimeError` if it was not."""
        if not self.is_success:
            raise RuntimeError("Query was not successful", self._errors)

    @property
    def is_success(self) -> bool:
        """Whether the query was successful."""
        return len(self._errors) == 0

    @property
    def errors(self) -> list[BfabricRequestError]:
        """List of errors that occurred during the query. An empty list indicates success."""
        return self._errors

    def extend(self, other: ResultContainer, reset_total_pages_api: bool = False) -> None:
        """Merges the results of `other` into this container.
        :param other: The container whose elements to append to the end of this container
        :param reset_total_pages_api: If True, the total_pages_api attribute will be reset to None
        """
        self.results += other.results
        self._errors += other.errors
        if reset_total_pages_api:
            self._total_pages_api = None
        elif self._total_pages_api != other.total_pages_api:
            logger.warning(
                f"Results observed with different total pages counts: "
                f"{self._total_pages_api} != {other.total_pages_api}"
            )

    @property
    def total_pages_api(self) -> int | None:
        """Number of pages available from the API."""
        return self._total_pages_api

    def to_list_dict(self, drop_empty: bool = False) -> list[dict[str, Any]]:
        """
        Converts the results to a list of dictionaries.
        :param drop_empty: If True, empty attributes will be removed from the results
        """
        if drop_empty:
            return formatter.drop_empty_elements(self.results, inplace=False)
        else:
            return self.results

    def to_polars(self, drop_empty: bool = False) -> polars.DataFrame:
        """Returns the results as a polars DataFrame.
        :param drop_empty: If True, empty attributes will be removed from the results
        """
        import polars

        return polars.DataFrame(self.to_list_dict(drop_empty=drop_empty))
