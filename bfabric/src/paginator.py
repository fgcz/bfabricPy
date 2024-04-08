from typing import Dict, Union, List, Any
from copy import deepcopy

BFABRIC_QUERY_LIMIT = 100


def read(engine, endpoint: str, query: dict = None) -> List[Dict]:
    """
    Make a query to the engine. Determine the number of pages. Make calls for every page, concatenate results
    :param engine: A BFabric API engine
    :param endpoint: endpoint
    :param query: query dictionary
    :return: List of responses
    """


    # Get the first page
    response = engine.read_object(endpoint, query, plain=True)
    nPages = response["numberofpages"]

    # Return empty list if nothing found
    if not nPages:
        return []

    # Get results from other pages as well, if need be
    # NOTE: Page numbering starts at 1
    responseLst = response[endpoint]
    for iPage in range(2, nPages+1):
        print('-- reading page', iPage, 'of', nPages)

        responseLst += engine.read_object(endpoint, query, page=iPage)

    return responseLst


# TODO: Is this scope sufficient? Is there ever more than one mutiquery parameter, and/or not at the root of dict?
def read_multi(engine, endpoint: str, query: dict, multiQueryKey: str, multiQueryVals: list) -> List[Dict]:
    """
    Makes a 1-parameter multi-query (there is 1 parameter that takes a list of values)
    Since the API only allows 100 queries per page, split the list into chunks before querying
    :param engine: A BFabric API engine
    :param endpoint: endpoint
    :param multiQueryKey:  key for which the multi-query is performed
    :param multiQueryVals: list of values for which the multi-query is performed
    :return: List of responses, concatenated over all multiquery values and all pages

    NOTE: It is assumed that there is only 1 response for each value.
    TODO: Test what happens if there are multiple responses. Is read_multi even necessary? Maybe the API would
      paginate by itself?
    """

    responseLst = []
    queryThis = deepcopy(query)   # Make a copy of the query, not to make edits to the argument

    for i in range(0, len(multiQueryVals), BFABRIC_QUERY_LIMIT):
        # Limit the multi-query parameter to an acceptable chunk size
        queryThis[multiQueryKey] = multiQueryVals[i:i + BFABRIC_QUERY_LIMIT]
        responseLst += read(engine, endpoint, queryThis)

    return responseLst


def save_multi(engine, endpoint: str, objLst: list) -> List[Dict]:
    # We must account for the possibility that the number of query values exceeds the BFabric maximum,
    # so we must split it into smaller chunks

    responseLst = []
    for i in range(0, len(objLst), BFABRIC_QUERY_LIMIT):
        objLstThis = objLst[i:i + BFABRIC_QUERY_LIMIT]
        responseLst += engine.save_object(endpoint, objLstThis)

    return responseLst


def delete_multi(engine, endpoint: str, idLst: list) -> List[Dict]:
    if len(idLst) == 0:
        print('Warning, empty list provided for deletion, ignoring')
        return []

    responseLst = []
    for i in range(0, len(idLst), BFABRIC_QUERY_LIMIT):
        idLstThis = idLst[i:i + BFABRIC_QUERY_LIMIT]
        responseLst += engine.delete_object(endpoint, idLstThis)

    return responseLst
