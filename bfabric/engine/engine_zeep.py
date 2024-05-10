from __future__ import annotations
import copy
from typing import Any

import zeep
from zeep.helpers import serialize_object

from bfabric.bfabric_config import BfabricAuth
from bfabric.errors import BfabricRequestError, get_response_errors
from bfabric.src.result_container import ResultContainer, _clean_result


class EngineZeep:
    """B-Fabric API Zeep Engine"""

    def __init__(self, base_url: str) -> None:
        self._cl = {}
        self._base_url = base_url

    def read(
        self,
        endpoint: str,
        obj: dict,
        auth: BfabricAuth,
        page: int = 1,
        idonly: bool = False,
        includedeletableupdateable: bool = False,
    ) -> ResultContainer:
        query = copy.deepcopy(obj)
        query["includedeletableupdateable"] = includedeletableupdateable

        # FIXME: Hacks for the cases where Zeep thinks a parameter is compulsory and it is actually not
        if endpoint == "sample":
            excl_keys = [
                "includefamily",
                "includeassociations",
                "includeplates",
                "includeresources",
                "includeruns",
                "includechildren",
                "includeparents",
                "includereplacements",
            ]
            _zeep_query_append_skipped(query, excl_keys, inplace=True, overwrite=False)

        full_query = dict(login=auth.login, page=page, password=auth.password, query=query, idonly=idonly)

        client = self._get_client(endpoint)
        with client.settings(strict=False, xml_huge_tree=True, xsd_ignore_sequence_order=True):
            response = client.service.read(full_query)
        return self._convert_results(response=response, endpoint=endpoint)

    def readid(
        self, endpoint: str, obj: dict, auth: BfabricAuth, page: int = 1, includedeletableupdateable: bool = True
    ) -> ResultContainer:
        raise NotImplementedError("Attempted to use a method `readid` of Zeep, which does not exist")

    def save(self, endpoint: str, obj: dict, auth: BfabricAuth) -> ResultContainer:
        query = copy.deepcopy(obj)

        # FIXME: Hacks for the cases where Zeep thinks a parameter is compulsory and it is actually not
        if endpoint == "resource":
            excl_keys = ["name", "sampleid", "storageid", "workunitid", "relativepath"]
            _zeep_query_append_skipped(query, excl_keys, inplace=True, overwrite=False)

        full_query = {"login": auth.login, "password": auth.password, endpoint: query}

        client = self._get_client(endpoint)

        try:
            with client.settings(strict=False):
                response = client.service.save(full_query)
        except AttributeError as e:
            if e.args[0] == "Service has no operation 'save'":
                raise BfabricRequestError(f"ZEEP failed to find save method for the {endpoint} endpoint.") from e
            raise e
        return self._convert_results(response=response, endpoint=endpoint)

    def delete(self, endpoint: str, id: int | list[int], auth: BfabricAuth) -> ResultContainer:
        if isinstance(id, list) and len(id) == 0:
            print("Warning, attempted to delete an empty list, ignoring")
            # TODO maybe use error here (and make sure it's consistent)
            return ResultContainer([], total_pages_api=0)

        query = {"login": auth.login, "password": auth.password, "id": id}

        client = self._get_client(endpoint)
        response = client.service.delete(query)
        return self._convert_results(response=response, endpoint=endpoint)

    def _get_client(self, endpoint: str) -> zeep.Client:
        if endpoint not in self._cl:
            wsdl = "".join((self._base_url, "/", endpoint, "?wsdl"))
            self._cl[endpoint] = zeep.Client(wsdl)
        return self._cl[endpoint]

    def _convert_results(self, response: Any, endpoint: str) -> ResultContainer:
        try:
            n_available_pages = response["numberofpages"]
        except AttributeError:
            n_available_pages = 0
        errors = get_response_errors(response, endpoint=endpoint)
        if not hasattr(response, endpoint):
            return ResultContainer([], total_pages_api=0, errors=errors)
        # TODO up until here it's duplicated with engine_suds
        results = []
        for result in response[endpoint]:
            results_parsed = dict(serialize_object(result, target_cls=dict))
            results_parsed = _clean_result(
                results_parsed,
                drop_underscores_suds=False,  # NOTE: Underscore problem specific to SUDS
                sort_responses=True,
            )
            results += [results_parsed]
        return ResultContainer(results=results, total_pages_api=n_available_pages, errors=errors)


# TODO: Check if this is a bug of BFabric or Zeep. Specifically, see if the same call to bFabricPy has the same bug
def _zeep_query_append_skipped(query: dict, skipped_keys: list, inplace: bool = False, overwrite: bool = False) -> dict:
    """
    This function is used to fix a buggy behaviour of Zeep/BFabric. Specifically, Zeep does not return correct
    query results if some of the optional parameters are not mentioned in the query.

    :param query:         Original query
    :param skipped_keys:  Optional keys to skip
    :param inplace:       Whether to change the argument, or make a new copy to return
    :param overwrite:     Whether to overwrite the key if it is already present in the query
    :return:              Adds optional keys to query as skipped values.
    """
    query_this = copy.deepcopy(query) if not inplace else query
    for key in skipped_keys:
        if overwrite or (key not in query_this.keys()):
            query_this[key] = zeep.xsd.SkipValue
    return query_this
