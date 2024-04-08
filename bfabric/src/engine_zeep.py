from typing import Union, List

import zeep
import copy


# TODO: Check if this is a bug of BFabric or Zeep. Specifically, see if the same call to bFabricPy has the same bug
def _zeep_query_append_skipped(query: dict, skippedKeys: list) -> dict:
    """
    This function is used to fix a buggy behaviour of Zeep/BFabric. Specifically, Zeep does not return correct
    query results if some of the optional parameters are not mentioned in the query.

    :param query:         Original query
    :param skippedKeys:   Optional keys to skip
    :return:              Adds optional keys to query as skipped values.
    """
    queryThis = query.copy()
    for key in skippedKeys:
        queryThis[key] = zeep.xsd.SkipValue
    return queryThis


class EngineZeep(object):
    """B-Fabric API SUDS Engine"""

    def __init__(self, login: str, password: str, webbase: str):
        self.cl = {}
        self.login = login
        self.password = password
        self.webbase = webbase

    def _get_client(self, endpoint: str):
        try:
            if not endpoint in self.cl:
                wsdl = "".join((self.webbase, '/', endpoint, "?wsdl"))
                self.cl[endpoint] = zeep.Client(wsdl)
                return self.cl[endpoint]
        except Exception as e:
            print(e)
            raise

    def read(self, endpoint: str, obj: dict, page: int = 1, includedeletableupdateable: bool = True):
        query = copy.deepcopy(obj)
        if includedeletableupdateable:
            query['includedeletableupdateable'] = True

        query = dict(login=self.login, page=page, password=self.password, query=query)

        client = self._get_client(endpoint)
        with client.settings(strict=False):
            return client.service.read(query)

    def readid(self, endpoint: str, obj: dict, page: int = 1, includedeletableupdateable: bool = True):
        raise NotImplementedError("Attempted to use a method `readid` of Zeep, which does not exist")

    def save(self, endpoint: str, obj: dict, skippedKeys: list = None):
        query = {'login': self.login, 'password': self.password, endpoint: obj}

        # If necessary, add skipped keys to the query
        if skippedKeys is not None:
            query = _zeep_query_append_skipped(query, skippedKeys)

        client = self._get_client(endpoint)
        with client.settings(strict=False):
            return client.service.save(query)

    def delete(self, endpoint: str, id: Union[int, List]):
        if isinstance(id, list) and len(id) == 0:
            print("Warning, attempted to delete an empty list, ignoring")
            return []

        query = {'login': self.login, 'password': self.password, 'id': id}

        client = self._get_client(endpoint)
        return client.service.delete(query)
