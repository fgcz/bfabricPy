# Single page query limit for BFabric API (as of time of writing, adapt if it changes)
BFABRIC_QUERY_LIMIT = 100

def page_iter(objs: list, page_size: int = BFABRIC_QUERY_LIMIT) -> list:
    """
    :param objs:       A list of objects to provide to bfabric as part of a query
    :param page_size:  Number of objects per page
    :return:           An iterator over chunks that would be sent to bfabric, 1 chunk per query
    """

    for i in range(0, len(objs), page_size):
        yield objs[i:i + page_size]
