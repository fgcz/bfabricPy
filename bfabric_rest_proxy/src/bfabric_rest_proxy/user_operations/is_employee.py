from __future__ import annotations

from bfabric import Bfabric
from bfabric.entities import User


def is_employee(user_client: Bfabric) -> bool:
    """Return True iff the authenticated user is an employee on the current B-Fabric instance.

    Delegates the actual check to :attr:`bfabric.entities.User.is_employee`; this helper
    just locates the user record associated with the authenticated login.

    :param user_client: the authenticated B-Fabric client whose user record to inspect
    :return: whether the user is an FGCZ employee
    :raises RuntimeError: if no user record (or more than one) is found for the login
    """
    login = user_client.auth.login
    entities = user_client.reader.query("user", {"login": login}, max_results=2)
    users = [u for u in entities.values() if isinstance(u, User)]
    if not users:
        raise RuntimeError(f"User record not found for login: {login}")
    if len(users) > 1:
        raise RuntimeError(f"Expected exactly one user for login {login}, got {len(users)}")
    return users[0].is_employee
