from __future__ import annotations
from typing import Union, List
import copy

from suds.client import Client
from suds import MethodNotFound
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
        obj: dict,
        auth: BfabricAuth,
        page: int = 1,
        idonly: bool = False,
        includedeletableupdateable: bool = False,
    ):
        """
        A generic method which can connect to any endpoint, e.g., workunit, project, order,
        externaljob, etc, and returns the object with the requested id.
        obj is a python dictionary which contains all the attributes of the endpoint
        for the "query".
        """
        query = copy.deepcopy(obj)
        query["includedeletableupdateable"] = includedeletableupdateable

        full_query = dict(login=auth.login, page=page, password=auth.password, query=query, idonly=idonly)
        client = self._get_client(endpoint)
        return client.service.read(full_query)

    # TODO: How is client.service.readid different from client.service.read. Do we need this method?
    def readid(self, endpoint: str, obj: dict, auth: BfabricAuth, page: int = 1):
        query = dict(login=auth.login, page=page, password=auth.password, query=obj)

        client = self._get_client(endpoint)
        return client.service.readid(query)

    def save(self, endpoint: str, obj: dict, auth: BfabricAuth):
        query = {"login": auth.login, "password": auth.password, endpoint: obj}

        client = self._get_client(endpoint)
        try:
            res = client.service.save(query)
        except MethodNotFound as e:
            raise BfabricRequestError(f"SUDS failed to find save method for the {endpoint} endpoint.") from e
        return res

    def delete(self, endpoint: str, id: Union[int, List], auth: BfabricAuth):
        if isinstance(id, list) and len(id) == 0:
            print("Warning, attempted to delete an empty list, ignoring")
            return []

        query = {"login": auth.login, "password": auth.password, "id": id}

        client = self._get_client(endpoint)
        return client.service.delete(query)

    def _get_client(self, endpoint: str) -> ServiceProxy:
        """Returns a SUDS service client for the given endpoint. Reuses existing instances when possible."""
        if endpoint not in self.cl:
            wsdl = "".join((self.base_url, "/", endpoint, "?wsdl"))
            self.cl[endpoint] = Client(wsdl, cache=None)
        return self.cl[endpoint]
