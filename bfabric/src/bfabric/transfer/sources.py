"""Resource -> transport source binding.

Maps a B-Fabric :class:`~bfabric.entities.Resource` onto the flat, transport-only
``bfabric.transfer._generic`` source types. This is the domain half of the split: it knows B-Fabric storage
URLs and preference order; the generic mover knows how to move bytes. Uses only ``httpx`` transitively
(via the read of the storage ``access`` record through the client), so it is plain core -- a
download-only / query consumer can import this with nothing extra installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, get_args

from bfabric.transfer._generic.sources import TransferSource, TransferSourceHttp, TransferSourceSsh

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bfabric import Bfabric
    from bfabric.entities import Resource

Transport = Literal["ssh", "http"]
"""A transport this binding can build a download source for from a B-Fabric resource.

Mirrors the ``type`` discriminators of the generic source models; the single place to add a new
transport (the ``resource_sources`` default and its ``allow`` filter both derive from it).
"""


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


def resource_sources(
    resource: Resource,
    client: Bfabric | None = None,
    *,
    allow: Iterable[Transport] | None = None,
) -> list[TransferSource]:
    """Enumerate the candidate transfer sources for ``resource``, best (fastest) first.

    ``allow`` constrains which transports may be constructed (e.g. ``{"http"}`` for the programmatic
    "force HTTP" override); ``None`` means all. v1 returns the constructible candidates in preference
    order (ssh before the HTTP anywhere-fallback); runtime availability probing (negotiation) is
    deferred. A ``client`` is required to construct an HTTP source (it reads the storage access
    record).
    """
    allowed = set(allow) if allow is not None else set(get_args(Transport))
    sources: list[TransferSource] = []
    if "ssh" in allowed:
        sources.append(ssh_source(resource))
    if "http" in allowed:
        if client is None:
            raise ValueError("A client is required to construct an HTTP source.")
        sources.append(http_source(resource, client))
    if not sources:
        raise ValueError(f"No transfer source could be constructed for the allowed transports {sorted(allowed)}.")
    return sources
