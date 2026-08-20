from __future__ import annotations

from collections.abc import Mapping

from loguru import logger

from bfabric.results.result_container import ResultContainer
from bfabric.utils.paginator import BFABRIC_QUERY_LIMIT, page_iter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bfabric.bfabric import Bfabric
    from bfabric.typing import ApiRequestDataType, ApiRequestObjectType


def _count_query_elements(value: ApiRequestDataType) -> int:
    """Returns how many elements `value` contributes to the API's query limit, summing nested containers.

    Over-counting only costs an extra request, whereas under-counting makes the API reject the query.
    """
    if isinstance(value, Mapping):
        return sum(_count_query_elements(item) for item in value.values())
    if isinstance(value, list | tuple):
        return sum(_count_query_elements(item) for item in value)
    return 1


class MultiQuery:
    """Some advanced functionality that supports paginating over a list of conditions that is larger than the 100
    conditions limit of the API.
    This functionality might eventually be merged into the main Bfabric class but will probably be subject to some
    breaking changes and is not as thoroughly tested as the main classes functionality.
    """

    def __init__(self, client: Bfabric) -> None:
        self._client = client

    # TODO: Is this scope sufficient? Is there ever more than one multi-query parameter, and/or not at the root of dict?
    def read_multi(
        self,
        endpoint: str,
        obj: ApiRequestObjectType,
        multi_query_key: str,
        multi_query_vals: Sequence[ApiRequestDataType],
        return_id_only: bool = False,
    ) -> ResultContainer:
        """Performs a 1-parameter multi-query, i.e. `multi_query_key` is the one `obj` field taking a list of values.

        The API allows at most BFABRIC_QUERY_LIMIT elements per query and counts the values of the other `obj` fields
        towards that limit too, so the values are split into chunks of the remaining size.
        :raises ValueError: if the other fields of `obj` already use up the element limit

        NOTE: It is assumed that there is only 1 response for each value.
        """
        # TODO add `check` parameter
        response_tot = ResultContainer([], total_pages_api=0, errors=[])
        # `multi_query_key` is set per chunk below, so only the other fields reserve elements.
        base_query = {key: value for key, value in obj.items() if key != multi_query_key}
        n_reserved = _count_query_elements(base_query)
        page_size = BFABRIC_QUERY_LIMIT - n_reserved
        if page_size < 1:
            msg = (
                f"The query fields {sorted(base_query)} already use {n_reserved} of the {BFABRIC_QUERY_LIMIT} query "
                f"elements allowed by the API, leaving no room for {multi_query_key!r} values."
            )
            raise ValueError(msg)

        # TODO the case of multiple responses per value is untested, and there is no `max_results` here, so a query
        #   matching a pattern instead of reading by id can accidentally pull the whole database
        for page_vals in page_iter(multi_query_vals, page_size=page_size):
            query = {**base_query, multi_query_key: page_vals}
            response_this = self._client.read(endpoint, query, max_results=None, return_id_only=return_id_only)
            response_tot.extend(response_this, reset_total_pages_api=True)

        return response_tot

    # NOTE: Save-multi method is likely useless. When saving multiple objects, they all have different fields.
    #    One option would be to provide a dataframe, but it might struggle with nested dicts
    #    Likely best solution is to not provide this method, and let users run a for-loop themselves.
    # def save_multi(self, endpoint: str, obj_lst: list, **kwargs) -> ResultContainer:
    #     response_tot = ResultContainer([], self.result_type, total_pages_api = 0)
    #
    #     # Iterate over request chunks that fit into a single API page
    #     for page_objs in page_iter(obj_lst):
    #         response_page = self.save(endpoint, page_objs, **kwargs)
    #         response_tot.extend(response_page, reset_total_pages_api=True
    #
    #     return response_tot

    def delete_multi(self, endpoint: str, id_list: list[int]) -> ResultContainer:
        """Deletes multiple objects from `endpoint` by their ids."""
        # TODO document and test error handling
        # TODO add `check` parameter
        response_tot = ResultContainer([], total_pages_api=0, errors=[])

        if not id_list:
            logger.warning("empty list provided for deletion, ignoring")
            return response_tot

        # Iterate over request chunks that fit into a single API page
        for page_ids in page_iter(id_list):
            response_page = self._client.delete(endpoint, page_ids)
            response_tot.extend(response_page, reset_total_pages_api=True)

        return response_tot

    def exists_multi(self, endpoint: str, key: str, value: list[int | str] | int | str) -> bool | list[bool]:
        """
        :param endpoint:  endpoint
        :param key:       A key for the query (e.g. id or name)
        :param value:     A value or a list of values
        :return:          Return a single bool or a list of bools for each value
            For each value, test if a key with that value is found in the API.
        """
        is_scalar = isinstance(value, int | str)
        if is_scalar:
            return self._client.exists(endpoint=endpoint, key=key, value=value, check=True)
        elif not isinstance(value, list):
            raise ValueError("Unexpected data type", type(value))

        # 1. Read data for this id
        results = self.read_multi(endpoint, {}, key, value)

        # 2. Extract all the ids for which there was a response
        result_vals = []
        for r in results.results:
            if key in r:
                result_vals += [r[key]]
            elif "_" + key in r:  # TODO: Remove this if SUDS bug is ever resolved
                result_vals += [r["_" + key]]

        # 3. For each of the requested ids, return true if there was a response and false if there was not
        return [val in result_vals for val in value]
