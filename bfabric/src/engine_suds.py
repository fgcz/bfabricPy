from typing import Union, List
import copy

from suds.client import Client


class EngineSUDS(object):
    """B-Fabric API SUDS Engine"""

    def __init__(self, login: str, password: str, base_url: str):
        self.cl = {}
        self.login = login
        self.password = password
        self.base_url = base_url

    def _get_client(self, endpoint: str):
        try:
            if not endpoint in self.cl:
                wsdl = "".join((self.base_url, '/', endpoint, "?wsdl"))
                self.cl[endpoint] = Client(wsdl, cache=None)
            return self.cl[endpoint]
        except Exception as e:
            print(e)
            raise

    def read(self, endpoint: str, obj: dict, page: int = 1, idonly: bool = False,
             includedeletableupdateable: bool = False):
        """
        A generic method which can connect to any endpoint, e.g., workunit, project, order,
        externaljob, etc, and returns the object with the requested id.
        obj is a python dictionary which contains all the attributes of the endpoint
        for the "query".
        """
        query = copy.deepcopy(obj)
        query['includedeletableupdateable'] = includedeletableupdateable

        full_query = dict(login=self.login, page=page, password=self.password, query=query,
                         idonly=idonly)

        client = self._get_client(endpoint)
        return client.service.read(full_query)

    # TODO: How is client.service.readid different from client.service.read. Do we need this method?
    def readid(self, endpoint: str, obj: dict, page: int = 1):
        query = dict(login=self.login, page=page, password=self.password, query=obj)

        client = self._get_client(endpoint)
        return client.service.readid(query)

    def save(self, endpoint: str, obj: dict):
        query = {'login': self.login, 'password': self.password, endpoint: obj}

        client = self._get_client(endpoint)
        return client.service.save(query)

    def delete(self, endpoint: str, id: Union[int, List]):
        if isinstance(id, list) and len(id) == 0:
            print("Warning, attempted to delete an empty list, ignoring")
            return []

        query = {'login': self.login, 'password': self.password, 'id': id}

        client = self._get_client(endpoint)
        return client.service.delete(query)
