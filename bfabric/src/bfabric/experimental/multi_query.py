from __future__ import annotations

from copy import deepcopy

from bfabric.results.result_container import ResultContainer
from bfabric.utils.paginator import page_iter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.bfabric import Bfabric


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
        obj: dict,
        multi_query_key: str,
        multi_query_vals: list,
        return_id_only: bool = False,
    ) -> ResultContainer:
        """Performs a 1-parameter multi-query (there is 1 parameter that takes a list of values)
        Since the API only allows BFABRIC_QUERY_LIMIT queries per page, split the list into chunks before querying
        :param endpoint: endpoint
        :param obj: query dictionary
        :param multi_query_key:  key for which the multi-query is performed
        :param multi_query_vals: list of values for which the multi-query is performed
        :param return_id_only: whether to return only the ids of the objects
        :return: List of responses, packaged in the results container

        NOTE: It is assumed that there is only 1 response for each value.
        """
        # TODO add `check` parameter
        response_tot = ResultContainer([], total_pages_api=0, errors=[])
        obj_extended = deepcopy(obj)  # Make a copy of the query, not to make edits to the argument

        # Iterate over request chunks that fit into a single API page
        for page_vals in page_iter(multi_query_vals):
            obj_extended[multi_query_key] = page_vals

            # TODO: Test what happens if there are multiple responses to each of the individual queries.
            #     * What would happen?
            #     * What would happen if total number of responses would exceed 100 now?
            #     * What would happen if we naively made a multi-query with more than 100 values? Would API paginate
            #       automatically? If yes, perhaps we don't need this method at all?
            # TODO: It is assumed that a user requesting multi_query always wants all of the pages. Can anybody think of
            #   exceptions to this? -> yes, when not reading by id but for instance matching a pattern, one might not
            #   be aware that they might accidentally pull the whole db, so it's better to have max_results here as well
            #   but it is not completely trivial to implement
            response_this = self._client.read(endpoint, obj_extended, max_results=None, return_id_only=return_id_only)
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
            print("Warning, empty list provided for deletion, ignoring")
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
        is_scalar = isinstance(value, (int, str))
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
