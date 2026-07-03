from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceHttp,
    FileSourceHttpValue,
    FileSourceSsh,
    FileSourceSshValue,
)

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import Resource, Storage


def _storage_of(resource: Resource) -> Storage:
    """Returns the resource's storage entity.

    The single place that works around the ``HasOne`` descriptor typing quirk (see
    ``bfabric/entities/core/has_one.py``): every ``resource.storage`` access otherwise raises a
    ``reportAttributeAccessIssue``, so callers here go through this helper instead of casting inline.
    """
    return cast("Storage", resource.storage)  # pyright: ignore[reportAttributeAccessIssue]


def get_ssh_file_source(resource: Resource) -> FileSourceSsh:
    """Get the SSH file source for a given resource."""
    storage = _storage_of(resource)
    return FileSourceSsh(ssh=FileSourceSshValue(host=str(storage["host"]), path=str(resource.storage_absolute_path)))


def get_http_file_source(resource: Resource, client: Bfabric) -> FileSourceHttp:
    """Get the HTTP file source for a given resource.

    Looks up the storage's HTTP access record and builds the download URL. The token is not resolved here;
    it is applied at prepare time (``auth="bfabric"`` marks the URL as needing the B-Fabric bearer token).
    """
    storage = _storage_of(resource)
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
    return FileSourceHttp(http=FileSourceHttpValue(url=url, auth="bfabric"))
