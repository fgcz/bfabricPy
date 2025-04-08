from __future__ import annotations
import copy
from typing import Any, TYPE_CHECKING

import requests
import zeep
from zeep.helpers import serialize_object

from bfabric.errors import BfabricRequestError, get_response_errors
from bfabric.results.response_delete import ResponseDelete
from bfabric.results.result_container import ResultContainer
from bfabric.results.response_format_dict import clean_result, drop_empty_elements

if TYPE_CHECKING:
    from bfabric.config import BfabricAuth


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
        return_id_only: bool = False,
        include_deletable_and_updatable_fields: bool = False,
    ) -> ResultContainer:
        """Reads the requested `obj` from `endpoint`.
        :param endpoint: the endpoint to read from, e.g. "sample"
        :param obj: a dictionary containing the query, for every field multiple possible values can be provided, the
            final query requires the condition for each field to be met
        :param auth: the authentication handle of the user performing the request
        :param page: the page number to read
        :param return_id_only: whether to return only the ids of the objects
        :param include_deletable_and_updatable_fields: whether to include the deletable and updatable fields
        """
        query = copy.deepcopy(obj)
        query["includedeletableupdateable"] = include_deletable_and_updatable_fields

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

        full_query = dict(
            login=auth.login,
            page=page,
            password=auth.password.get_secret_value(),
            query=query,
            idonly=return_id_only,
        )

        client = self._get_client(endpoint)
        with client.settings(strict=False, xml_huge_tree=True, xsd_ignore_sequence_order=True):
            response = client.service.read(full_query)
        return self._convert_results(response=response, endpoint=endpoint)

    def save(self, endpoint: str, obj: dict, auth: BfabricAuth, method: str = "save") -> ResultContainer:
        """Saves the provided object to the specified endpoint.
        :param endpoint: the endpoint to save to, e.g. "sample"
        :param obj: the object to save
        :param auth: the authentication handle of the user performing the request
        :param method: the method to use for saving, generally "save", but in some cases e.g. "checkandinsert" is more
            appropriate to be used instead.
        """
        query = copy.deepcopy(obj)

        # FIXME: Hacks for the cases where Zeep thinks a parameter is compulsory and it is actually not
        if endpoint == "resource":
            excl_keys = ["name", "sampleid", "storageid", "workunitid", "relativepath"]
            _zeep_query_append_skipped(query, excl_keys, inplace=True, overwrite=False)

        full_query = {"login": auth.login, "password": auth.password.get_secret_value(), endpoint: query}

        client = self._get_client(endpoint)

        try:
            with client.settings(strict=False):
                response = getattr(client.service, method)(full_query)
        except AttributeError as e:
            if e.args[0] == "Service has no operation 'save'":
                raise BfabricRequestError(f"ZEEP failed to find save method for the {endpoint} endpoint.") from e
            raise e
        return self._convert_results(response=response, endpoint=endpoint)

    def delete(self, endpoint: str, id: int | list[int], auth: BfabricAuth) -> ResultContainer:
        """Deletes the object with the specified ID from the specified endpoint.
        :param endpoint: the endpoint to delete from, e.g. "sample"
        :param id: the ID of the object to delete
        :param auth: the authentication handle of the user performing the request
        """
        if isinstance(id, list) and len(id) == 0:
            return ResponseDelete.from_empty_request()

        query = {"login": auth.login, "password": auth.password.get_secret_value(), "id": id}
        client = self._get_client(endpoint)
        response = client.service.delete(query)
        return ResponseDelete.from_zeep(zeep_response=response, endpoint=endpoint)

    def _get_client(self, endpoint: str) -> zeep.Client:
        if endpoint not in self._cl:
            try:
                self._cl[endpoint] = zeep.Client(f"{self._base_url}/{endpoint}?wsdl")
            except requests.exceptions.HTTPError as error:
                if error.response is not None and error.response.status_code == 404:
                    msg = f"Non-existent endpoint {repr(endpoint)} or the configured B-Fabric instance was not found."
                    raise BfabricRequestError(msg) from error
                raise
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
            results_parsed = clean_result(
                results_parsed,
                drop_underscores_suds=False,  # NOTE: Underscore problem specific to SUDS
                sort_keys=True,
            )
            results_parsed = drop_empty_elements(results_parsed)
            results += [results_parsed]
        return ResultContainer(results=results, total_pages_api=n_available_pages, errors=errors)


# TODO: The reason why Zeep requires to explicitly skip certain values remains unclear
#    To the best of our current understanding, the fields are actually optional, but because of some differences in
#      formatting they appear to zeep as compulsory. The current solution is envisioned by developers of Zeep, but
#      it is a hack, and should ideally be handled internally by Zeep.
#    If developers of Zeep ever resume its maintenance, it would make sense to revisit
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
        if overwrite or (key not in query_this):
            query_this[key] = zeep.xsd.SkipValue
    return query_this
