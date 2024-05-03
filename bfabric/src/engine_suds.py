from __future__ import annotations
from typing import Union, List, Dict, Any
import copy

from suds import MethodNotFound
from suds.client import Client
from suds.serviceproxy import ServiceProxy

from bfabric.bfabric_config import BfabricAuth
from bfabric.src.errors import BfabricRequestError


class EngineSUDS:
    """B-Fabric API SUDS Engine"""

    def __init__(self, base_url: str):
        self.cl = {}
        self.base_url = base_url

    def read(
        self,
        endpoint: str,
        obj: Dict[str, Any],
        auth: BfabricAuth,
        page: int = 1,
        idonly: bool = False,
        includedeletableupdateable: bool = False,
    ):
        """Reads the requested `obj` from `endpoint`.
        :param endpoint: the endpoint to read, e.g. `workunit`, `project`, `order`, `externaljob`, etc.
        :param obj: a python dictionary which contains all the attribute values that have to match
        :param auth: the authentication handle of the user performing the request
        :param page: the page number to read
        :param idonly: whether to return only the ids of the objects
        :param includedeletableupdateable: TODO
        """
        query = copy.deepcopy(obj)
        query["includedeletableupdateable"] = includedeletableupdateable

        full_query = dict(login=auth.login, page=page, password=auth.password, query=query, idonly=idonly)
        service = self._get_suds_service(endpoint)
        return service.read(full_query)

    # TODO: How is client.service.readid different from client.service.read. Do we need this method?
    def readid(self, endpoint: str, obj: dict, auth: BfabricAuth, page: int = 1):
        query = dict(login=auth.login, page=page, password=auth.password, query=obj)
        service = self._get_suds_service(endpoint)
        return service.readid(query)

    def save(self, endpoint: str, obj: dict, auth: BfabricAuth):
        query = {"login": auth.login, "password": auth.password, endpoint: obj}
        service = self._get_suds_service(endpoint)
        try:
            res = service.save(query)
        except MethodNotFound as e:
            raise BfabricRequestError(f"SUDS failed to find save method for the {endpoint} endpoint.") from e
        return res

    def delete(self, endpoint: str, id: Union[int, List], auth: BfabricAuth):
        if isinstance(id, list) and len(id) == 0:
            print("Warning, attempted to delete an empty list, ignoring")
            return []

        query = {"login": auth.login, "password": auth.password, "id": id}
        service = self._get_suds_service(endpoint)
        return service.delete(query)

    def _get_suds_service(self, endpoint: str) -> ServiceProxy:
        """Returns a SUDS service for the given endpoint. Reuses existing instances when possible."""
        if endpoint not in self.cl:
            wsdl = "".join((self.base_url, "/", endpoint, "?wsdl"))
            self.cl[endpoint] = Client(wsdl, cache=None)
        return self.cl[endpoint].service

