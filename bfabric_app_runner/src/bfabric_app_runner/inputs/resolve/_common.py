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


def get_ssh_file_source(resource: Resource) -> FileSourceSsh:
    """Get the SSH file source for a given resource."""
    return FileSourceSsh(
        ssh=FileSourceSshValue(host=resource.storage["host"], path=str(resource.storage_absolute_path))
    )


def get_http_file_source(resource: Resource, client: Bfabric) -> FileSourceHttp:
    """Get the HTTP file source for a given resource.

    Looks up the storage's HTTP access record and builds the download URL. The token is not resolved here;
    it is applied at prepare time (``auth="bfabric"`` marks the URL as needing the B-Fabric bearer token).
    """
    storage = cast("Storage", resource.storage)  # pyright: ignore[reportAttributeAccessIssue]
    storage_id = storage.id
    records = client.read("access", {"storageid": storage_id, "type": "HTTP"})
    if not records:
        raise ValueError(
            f"Storage {storage_id} has no HTTP access configured; cannot fetch resource {resource.id} over HTTP."
        )
    access = records[0]
    # Normalize the basepath/relativepath boundary to exactly one slash (B-Fabric stores relativepath
    # with a leading slash, mirroring Resource.storage_relative_path which lstrips it for the SSH path).
    basepath = str(access["basepath"]).rstrip("/")
    relativepath = str(resource["relativepath"]).lstrip("/")
    url = f"{access['protocol']}://{access['host']}{basepath}/{relativepath}"
    return FileSourceHttp(http=FileSourceHttpValue(url=url, auth="bfabric"))
