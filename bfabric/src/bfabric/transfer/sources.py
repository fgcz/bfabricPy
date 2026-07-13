"""Resource -> transport source binding.

Maps a B-Fabric :class:`~bfabric.entities.Resource` onto the flat, transport-only
``bfabric.transfer._generic`` source types. This is the domain half of the split: it knows B-Fabric storage
URLs; the generic mover knows how to move bytes. Uses only ``httpx`` transitively
(via the read of the storage ``access`` record through the client), so it is plain core -- a
download-only / query consumer can import this with nothing extra installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.transfer._generic.sources import TransferSourceHttp, TransferSourceSsh

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import Resource


def ssh_source(resource: Resource) -> TransferSourceSsh:
    """Build the ssh/rsync/scp source for ``resource`` from its storage host + absolute path."""
    storage = resource.storage
    return TransferSourceSsh(host=str(storage["host"]), path=str(resource.storage_absolute_path))


def http_source(resource: Resource, client: Bfabric) -> TransferSourceHttp:
    """Build the whole-file HTTP source for ``resource`` from its storage's HTTP access record.

    The bearer token is not resolved here; ``auth="bfabric"`` marks the URL as needing the B-Fabric
    access token, which the mover applies (and only to this URL) at transfer time.
    """
    storage = resource.storage
    records = client.read("access", {"storageid": storage.id, "type": "HTTP"})
    if not records:
        raise ValueError(
            f"Storage {storage.id} has no HTTP access configured; cannot fetch resource {resource.id} over HTTP."
        )
    access = records[0]
    # Join the access basepath (leading/trailing slashes vary) to the resource's relative path with
    # exactly one slash; storage_relative_path already strips the leading slash B-Fabric stores.
    basepath = str(access["basepath"]).rstrip("/")
    url = f"{access['protocol']}://{access['host']}{basepath}/{resource.storage_relative_path.as_posix()}"
    return TransferSourceHttp(url=url, auth="bfabric")
