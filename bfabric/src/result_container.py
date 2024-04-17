# NOTE: This allows class type annotations inside the same class. According to
#    https://stackoverflow.com/questions/44798635/how-can-i-set-the-same-type-as-class-in-methods-parameter-following-pep484
# this should become default behaviour in one of the future versions of python. Remove this import
# once it is no longer necessary
from __future__ import annotations
from enum import Enum

from zeep.helpers import serialize_object

from bfabric.src.suds_format import suds_asdict_recursive
from bfabric.src.iter_helper import drop_empty_response_elements, map_response_element_keys, sort_response_dicts


class BfabricResultType(Enum):
    LISTDICT = 1
    LISTSUDS = 2
    LISTZEEP = 3


def _clean_result(rez: dict, drop_empty: bool = True, drop_underscores_suds: bool = True,
                  have_sort_responses: bool = False) -> dict:
    if drop_empty:
        drop_empty_response_elements(rez, inplace=True)

    if drop_underscores_suds:
        map_response_element_keys(rez,
                                  {'_id': 'id', '_classname': 'classname', '_projectid': 'projectid'},
                                  inplace=True)
    if have_sort_responses:
        sort_response_dicts(rez, inplace=True)

    return rez


class ResultContainer:
    def __init__(self, results: list, result_type: BfabricResultType, total_pages_api: int = None):
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
        self.total_pages_api = total_pages_api

    def __getitem__(self, idx: int):
        return self.results[idx]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str(self.to_list_dict())

    def __len__(self):
        return len(self.results)

    def append(self, other: ResultContainer) -> None:
        """
        Can merge results of two queries. This can happen if the engine splits a complicated query in two
        :param other: The other query results that should be appended to this
        :return:
        """

        if self.result_type != other.result_type:
            raise ValueError("Attempting to merge results of two different types", self.result_type, other.result_type)

        self.results += other.results
        if (self.total_pages_api is not None) and (other.total_pages_api is not None):
            self.total_pages_api += other.total_pages_api
        else:
            self.total_pages_api = None

    def total_pages_api(self):
        return self.total_pages_api

    def to_list_dict(self, drop_empty: bool = True, drop_underscores_suds: bool = True,
                     have_sort_responses: bool = False):
        match self.result_type:
            case BfabricResultType.LISTDICT:
                return self.results
            case BfabricResultType.LISTSUDS:
                results = []
                for rez in self.results:
                    rez_parsed = suds_asdict_recursive(rez, convert_types=True)
                    rez_parsed = _clean_result(rez_parsed, drop_empty=drop_empty,
                                               drop_underscores_suds=drop_underscores_suds,
                                               have_sort_responses=have_sort_responses)
                    results += [rez_parsed]
                return results
            case BfabricResultType.LISTZEEP:
                results = []
                for rez in self.results:
                    rez_parsed = dict(serialize_object(rez, target_cls=dict))
                    rez_parsed = _clean_result(rez_parsed, drop_empty=drop_empty,
                                               drop_underscores_suds=False,               # NOTE: Underscore problem specific to SUDS
                                               have_sort_responses=have_sort_responses)
                    results += [rez_parsed]
                return results
            case _:
                raise ValueError("Unexpected results type", self.result_type)
