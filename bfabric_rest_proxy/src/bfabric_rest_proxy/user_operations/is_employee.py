from __future__ import annotations

from bfabric import Bfabric


def is_employee(user_client: Bfabric) -> bool:
    """Return True iff the authenticated user has a positive ``empdegree`` in B-Fabric.

    Non-employees typically lack the ``empdegree`` field entirely; employees have a numeric
    string whose float value is strictly greater than zero.

    :param user_client: the authenticated B-Fabric client whose user record to inspect
    :return: whether the user is an FGCZ employee
    :raises RuntimeError: if no user record is found for the authenticated login
    """
    res = user_client.read("user", {"login": user_client.auth.login})
    records = res.to_list_dict()
    if not records:
        raise RuntimeError(f"User record not found for login: {user_client.auth.login}")
    empdegree = records[0].get("empdegree")
    if not isinstance(empdegree, (str, int, float)) or isinstance(empdegree, bool):
        return False
    try:
        return float(empdegree) > 0
    except ValueError:
        return False
