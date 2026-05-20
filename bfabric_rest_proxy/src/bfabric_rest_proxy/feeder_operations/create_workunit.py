from __future__ import annotations

from bfabric import Bfabric
from bfabric.entities import Workunit
from bfabric.operations.workunit import CreateWorkunitParams
from bfabric.operations.workunit import create_workunit as _create_workunit

__all__ = ["CreateWorkunitParams", "CreateWorkunitRequest", "create_workunit"]


class CreateWorkunitRequest(CreateWorkunitParams):
    """Proxy-level request: core workunit params plus client-supplied audit metadata."""

    created_using: str | None = None


def create_workunit(
    user_client: Bfabric,
    feeder_client: Bfabric,
    request: CreateWorkunitRequest,
) -> Workunit:
    """Create a workunit using the feeder client on behalf of the user client.

    `Created For` is set server-side from the authenticated user.
    `Created Using` is set from the (optional) client-supplied field.
    """
    _check_container_access(user_client=user_client, container_id=request.container_id)
    audit_attributes = {"Created For": user_client.auth.login}
    if request.created_using is not None:
        audit_attributes["Created Using"] = request.created_using
    return _create_workunit(
        client=feeder_client,
        params=request,
        audit_attributes=audit_attributes,
    )


def _check_container_access(user_client: Bfabric, container_id: int) -> None:
    res_valid = user_client.read("container", {"id": container_id}, return_id_only=True, check=True)
    if len(res_valid) != 1 or res_valid[0]["id"] != container_id:
        msg = "Container authorization failed"
        raise RuntimeError(msg)
