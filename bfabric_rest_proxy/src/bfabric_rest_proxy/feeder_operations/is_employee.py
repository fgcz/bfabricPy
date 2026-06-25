from __future__ import annotations

from bfabric import Bfabric
from bfabric.entities import User


def is_employee(user_client: Bfabric, feeder_client: Bfabric) -> bool:
    """Return True iff the authenticated user is an employee on the current B-Fabric instance.

    The authenticated login is read from ``user_client``; the actual ``User`` record is
    looked up with the privileged ``feeder_client`` because the ``empdegree`` field is
    typically not readable with a regular user's web-service credentials.

    Delegates the actual check to :attr:`bfabric.entities.User.is_employee`.

    :param user_client: the authenticated B-Fabric client whose login identifies the user
    :param feeder_client: the privileged feeder client used to fetch the user record
    :return: whether the user is an employee
    :raises RuntimeError: if no user record is found for the login
    """
    login = user_client.auth.login
    user = User.find_by_login(login=login, client=feeder_client)
    if user is None:
        raise RuntimeError(f"User record not found for login: {login}")
    return user.is_employee
