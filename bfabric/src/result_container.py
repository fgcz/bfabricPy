# NOTE: This allows class type annotations inside the same class. According to
#    https://stackoverflow.com/questions/44798635/how-can-i-set-the-same-type-as-class-in-methods-parameter-following-pep484
# this should become default behaviour in one of the future versions of python. Remove this import
# once it is no longer necessary
from __future__ import annotations
from enum import Enum

from zeep.helpers import serialize_object

from bfabric.src.response_format_suds import suds_asdict_recursive
import bfabric.src.response_format_dict as formatter


class BfabricResultType(Enum):
    LISTDICT = 1
    LISTSUDS = 2
    LISTZEEP = 3


def _clean_result(rez: dict, drop_empty: bool = True, drop_underscores_suds: bool = True,
                  sort_responses: bool = False) -> dict:
    if drop_empty:
        formatter.drop_empty_elements(rez, inplace=True)

    if drop_underscores_suds:
        formatter.map_element_keys(rez,
                                  {'_id': 'id', '_classname': 'classname', '_projectid': 'projectid'},
                                  inplace=True)
    if sort_responses:
        formatter.sort_dicts_by_key(rez, inplace=True)

    return rez


class ResultContainer:
    def __init__(self, results: list, result_type: BfabricResultType, total_pages_api: int = None, errors: list = None):
        """
        :param results:    List of BFabric query results
        :param result_type: Format of each result (All must be of the same format)
        :param total_pages_api:  Maximal number of pages that were available for reading.
            NOTE: User may have requested to cap the total number of results. Thus, it may be of interest to know
            the (approximate) total number of results the API had for the query. The total number of results is
            somewhere between max_pages * (BFABRIC_QUERY_LIMIT - 1) and max_pages * BFABRIC_QUERY_LIMIT
        """
        self.results = results
        self.result_type = result_type
        self._total_pages_api = total_pages_api
        self._errors = errors or []

    def __getitem__(self, idx: int):
        return self.results[idx]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str(self.to_list_dict())

    def __len__(self):
        return len(self.results)

    def assert_success(self):
        if not self.is_success:
            raise RuntimeError("Query was not successful", self._errors)

    @property
    def is_success(self) -> bool:
        return len(self._errors) == 0

    @property
    def errors(self) -> list:
        return self._errors

    def extend(self, other: ResultContainer) -> None:
        """
        Can merge results of two queries. This can happen if the engine splits a complicated query in two
        :param other: The other query results that should be appended to this
        :return:
        """

        if self.result_type != other.result_type:
            raise ValueError("Attempting to merge results of two different types", self.result_type, other.result_type)

        self.results += other.results
        self._errors += other.errors
        if (self._total_pages_api is not None) and (other._total_pages_api is not None):
            self._total_pages_api += other._total_pages_api
        else:
            self._total_pages_api = None

    @property
    def total_pages_api(self):
        return self._total_pages_api

    def to_list_dict(self, drop_empty: bool = True, drop_underscores_suds: bool = True,
                     have_sort_responses: bool = False):
        """
        Converts the results to a list of dictionaries.
        :param drop_empty: If True, empty attributes will be removed from the results
        :param drop_underscores_suds: If True, leading underscores will be removed from the keys of the results
        :param have_sort_responses: If True, keys of dictionaries in the response will be sorted.
        TODO what about the order of items in the list?
        """
        if self.result_type == BfabricResultType.LISTDICT:
            return self.results
        elif self.result_type == BfabricResultType.LISTSUDS:
            results = []
            for rez in self.results:
                rez_parsed = suds_asdict_recursive(rez, convert_types=True)
                rez_parsed = _clean_result(rez_parsed, drop_empty=drop_empty,
                                           drop_underscores_suds=drop_underscores_suds,
                                           sort_responses=have_sort_responses)
                results += [rez_parsed]
            return results
        elif self.result_type == BfabricResultType.LISTZEEP:
            results = []
            for rez in self.results:
                rez_parsed = dict(serialize_object(rez, target_cls=dict))
                rez_parsed = _clean_result(rez_parsed, drop_empty=drop_empty,
                                           drop_underscores_suds=False,  # NOTE: Underscore problem specific to SUDS
                                           sort_responses=have_sort_responses)
                results += [rez_parsed]
            return results
        else:
            raise ValueError("Unexpected results type", self.result_type)
