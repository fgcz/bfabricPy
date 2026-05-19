from __future__ import annotations

from bfabric import Bfabric
from bfabric.entities import Workunit
from bfabric.operations.workunit import CreateWorkunitParams, create_workunit as _create_workunit

__all__ = ["CreateWorkunitParams", "create_workunit"]


def create_workunit(
    user_client: Bfabric,
    feeder_client: Bfabric,
    params: CreateWorkunitParams,
) -> Workunit:
    """Create a workunit with the given parameters, using the feeder client on behalf of the user client.

    Before proceeding, it will be checked if the user has permission to read the target container.

    :param user_client: the web application user, which initiates the operation
    :param feeder_client: the feeder user, which will actually perform the operation
    :param params: the workunit parameters
    :return: the created workunit
    :raise: BfabricException if any API operation fails
    :raise: RuntimeError if authorization fails
    """
    _check_container_access(user_client=user_client, container_id=params.container_id)
    return _create_workunit(
        client=feeder_client,
        params=params,
        audit_attributes={"WebApp User": user_client.auth.login},
    )


def _check_container_access(user_client: Bfabric, container_id: int) -> None:
    res_valid = user_client.read("container", {"id": container_id}, return_id_only=True, check=True)
    if len(res_valid) != 1 or res_valid[0]["id"] != container_id:
        msg = "Container authorization failed"
        raise RuntimeError(msg)
