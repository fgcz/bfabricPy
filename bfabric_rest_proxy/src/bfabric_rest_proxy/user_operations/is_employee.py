from __future__ import annotations

from bfabric import Bfabric
from bfabric.entities import User


def is_employee(user_client: Bfabric) -> bool:
    """Return True iff the authenticated user is an employee on the current B-Fabric instance.

    Delegates the actual check to :attr:`bfabric.entities.User.is_employee`; this helper
    just locates the user record associated with the authenticated login.

    :param user_client: the authenticated B-Fabric client whose user record to inspect
    :return: whether the user is an employee
    :raises RuntimeError: if no user record is found for the login
    """
    login = user_client.auth.login
    user = user_client.reader.query_one("user", {"login": login}, expected_type=User)
    if user is None:
        raise RuntimeError(f"User record not found for login: {login}")
    return user.is_employee
