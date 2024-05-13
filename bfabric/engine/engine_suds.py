from __future__ import annotations

import copy
from typing import Any

from suds import MethodNotFound
from suds.client import Client
from suds.serviceproxy import ServiceProxy

from bfabric.bfabric_config import BfabricAuth
from bfabric.engine.response_format_suds import suds_asdict_recursive
from bfabric.errors import BfabricRequestError, get_response_errors
from bfabric.results.result_container import _clean_result, ResultContainer


class EngineSUDS:
    """B-Fabric API SUDS Engine."""

    def __init__(self, base_url: str, drop_underscores: bool = True) -> None:
        self._cl = {}
        self._base_url = base_url
        self._drop_underscores = drop_underscores

    def read(
        self,
        endpoint: str,
        obj: dict[str, Any],
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

        full_query = dict(login=auth.login, page=page, password=auth.password, query=query, idonly=return_id_only)
        service = self._get_suds_service(endpoint)
        response = service.read(full_query)
        return self._convert_results(response=response, endpoint=endpoint)

    def save(self, endpoint: str, obj: dict, auth: BfabricAuth) -> ResultContainer:
        """Saves the provided object to the specified endpoint.
        :param endpoint: the endpoint to save to, e.g. "sample"
        :param obj: the object to save
        :param auth: the authentication handle of the user performing the request
        """
        query = {"login": auth.login, "password": auth.password, endpoint: obj}
        service = self._get_suds_service(endpoint)
        try:
            response = service.save(query)
        except MethodNotFound as e:
            raise BfabricRequestError(f"SUDS failed to find save method for the {endpoint} endpoint.") from e
        return self._convert_results(response=response, endpoint=endpoint)

    def delete(self, endpoint: str, id: int | list[int], auth: BfabricAuth) -> ResultContainer:
        """Deletes the object with the specified ID from the specified endpoint.
        :param endpoint: the endpoint to delete from, e.g. "sample"
        :param id: the ID of the object to delete
        :param auth: the authentication handle of the user performing the request
        """
        if isinstance(id, list) and len(id) == 0:
            print("Warning, attempted to delete an empty list, ignoring")
            # TODO maybe use error here (and make sure it's consistent)
            return ResultContainer([], total_pages_api=0)

        query = {"login": auth.login, "password": auth.password, "id": id}
        service = self._get_suds_service(endpoint)
        response = service.delete(query)
        return self._convert_results(response=response, endpoint=endpoint)

    def _get_suds_service(self, endpoint: str) -> ServiceProxy:
        """Returns a SUDS service for the given endpoint. Reuses existing instances when possible."""
        if endpoint not in self._cl:
            wsdl = "".join((self._base_url, "/", endpoint, "?wsdl"))
            self._cl[endpoint] = Client(wsdl, cache=None)
        return self._cl[endpoint].service

    def _convert_results(self, response: Any, endpoint: str) -> ResultContainer:
        try:
            n_available_pages = response["numberofpages"]
        except AttributeError:
            n_available_pages = 0
        errors = get_response_errors(response, endpoint=endpoint)
        if not hasattr(response, endpoint):
            return ResultContainer([], total_pages_api=0, errors=errors)
        # TODO up until here it's duplicated with engine_zeep
        results = []
        for result in response[endpoint]:
            result_parsed = suds_asdict_recursive(result, convert_types=True)
            result_parsed = _clean_result(
                result_parsed,
                drop_underscores_suds=self._drop_underscores,
                sort_responses=True,
            )
            results += [result_parsed]
        return ResultContainer(results=results, total_pages_api=n_available_pages, errors=errors)
