from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from bfabric.entities import Workunit

if TYPE_CHECKING:
    from bfabric import Bfabric


def complete_workunit(client: Bfabric, workunit_id: int) -> Workunit:
    result = client.save("workunit", {"id": workunit_id, "status": "available"})
    return Workunit(result[0], bfabric_instance=client.config.base_url)


def mark_workunit_failed(client: Bfabric, workunit_id: int) -> None:
    """Flip ``workunit_id`` to status ``failed`` as part of failure cleanup.

    Swallows (and logs) any error so it never masks the original exception being handled -- see the
    "Failure cleanup pattern" in operations_module.md.
    """
    try:
        _ = client.save("workunit", {"id": workunit_id, "status": "failed"})
    except BaseException as cleanup_error:  # noqa: BLE001 — cleanup must not mask the original error
        logger.error(f"Failed to mark workunit {workunit_id} failed during cleanup: {cleanup_error!r}")
