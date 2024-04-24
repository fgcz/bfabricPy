from typing import Union, List

import zeep
import copy


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


class EngineZeep:
    """B-Fabric API Zeep Engine"""

    def __init__(self, login: str, password: str, base_url: str):
        self.cl = {}
        self.login = login
        self.password = password
        self.base_url = base_url

    def _get_client(self, endpoint: str):
        try:
            if endpoint not in self.cl:
                wsdl = "".join((self.base_url, '/', endpoint, "?wsdl"))
                self.cl[endpoint] = zeep.Client(wsdl)
            return self.cl[endpoint]
        except Exception as e:
            print(e)
            raise

    def read(self, endpoint: str, obj: dict, page: int = 1, idonly: bool = False,
             includedeletableupdateable: bool = False):
        query = copy.deepcopy(obj)
        query['includedeletableupdateable'] = includedeletableupdateable

        # FIXME: Hacks for the cases where Zeep thinks a parameter is compulsory and it is actually not
        if endpoint == 'sample':
            excl_keys = ['includefamily', 'includeassociations', 'includeplates', 'includeresources', 'includeruns',
                         'includechildren', 'includeparents', 'includereplacements']
            _zeep_query_append_skipped(query, excl_keys, inplace=True, overwrite=False)

        full_query = dict(login=self.login, page=page, password=self.password, query=query, idonly=idonly)

        client = self._get_client(endpoint)
        with client.settings(strict=False, xml_huge_tree=True, xsd_ignore_sequence_order=True):
            return client.service.read(full_query)

    def readid(self, endpoint: str, obj: dict, page: int = 1, includedeletableupdateable: bool = True):
        raise NotImplementedError("Attempted to use a method `readid` of Zeep, which does not exist")

    def save(self, endpoint: str, obj: dict, skipped_keys: list = None):
        query = {'login': self.login, 'password': self.password, endpoint: obj}

        # If necessary, add skipped keys to the query
        if skipped_keys is not None:
            query = _zeep_query_append_skipped(query, skipped_keys)

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
