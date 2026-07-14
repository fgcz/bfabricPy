from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.transfer import http_source, ssh_source

from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceHttp,
    FileSourceHttpValue,
    FileSourceSsh,
    FileSourceSshValue,
)

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import Resource


def get_ssh_file_source(resource: Resource) -> FileSourceSsh:
    """Get the SSH file source (spec form) for a given resource, via the core transfer binding."""
    source = ssh_source(resource)
    return FileSourceSsh(ssh=FileSourceSshValue(host=source.host, path=source.path))


def get_http_file_source(resource: Resource, client: Bfabric) -> FileSourceHttp:
    """Get the HTTP file source (spec form) for a given resource, via the core transfer binding.

    The token is not resolved here; ``auth="bfabric"`` marks the URL as needing the B-Fabric bearer
    token, which prepare-time transfer applies.
    """
    source = http_source(resource, client)
    return FileSourceHttp(http=FileSourceHttpValue(url=source.url, auth=source.auth))
