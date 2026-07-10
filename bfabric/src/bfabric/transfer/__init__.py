"""The B-Fabric transfer layer: generic byte-movers plus the B-Fabric domain binding.

This single namespace unifies two internal halves:

- The **generic movers** (``bfabric.transfer._generic``) -- transport-only source/sink value objects,
  ``Credentials``, ``fetch_to_path`` (download) and ``send_to_sink`` (upload, tus behind ``[tus]``).
  They know nothing about B-Fabric and are re-exported here for convenience.
- The **domain binding** -- mapping B-Fabric objects onto those transport types:

  - ``resource_sources`` / ``ssh_source`` / ``http_source`` -- Resource -> download sources.
  - ``UploadRestClient`` + ``tus_sink_for_resource`` -- the ``/rest/upload/*`` calls -> a tus upload sink.
  - ``token_provider`` and the fail-fast OAuth scope pre-checks (``check_upload_scope`` / ``check_download_scope``).

Importing this module is plain core (httpx only); actually transferring over tus needs the
``bfabric[transfer]`` extra, and is dispatched lazily by ``send_to_sink``.
"""

from __future__ import annotations

from bfabric.transfer._generic import (
    Credentials,
    FileInfo,
    TransferError,
    TransferSink,
    TransferSinkLocal,
    TransferSinkScp,
    TransferSinkTus,
    TransferSource,
    TransferSourceHttp,
    TransferSourceLocal,
    TransferSourceSsh,
    UploadOutcome,
    collect_file_infos,
    compute_file_info,
    fetch_to_path,
    md5_checksum,
    resolve_paths,
    scp,
    send_to_sink,
)
from bfabric.transfer.errors import (
    BfabricTransferError,
    DuplicateCheckError,
    ResourceCreationError,
    ScopeError,
    UploadInitiationError,
)
from bfabric.transfer.sources import http_source, resource_sources, ssh_source
from bfabric.transfer.tokens import (
    check_download_scope,
    check_upload_scope,
    require_oauth,
    require_scope,
    token_provider,
)
from bfabric.transfer.upload import (
    CreatedResource,
    DuplicateResult,
    UploadRestClient,
    UploadTokenResult,
    api_to_rest_url,
    require_tus,
    tus_sink_for_resource,
)

__all__ = [
    "BfabricTransferError",
    "CreatedResource",
    "Credentials",
    "DuplicateCheckError",
    "DuplicateResult",
    "FileInfo",
    "ResourceCreationError",
    "ScopeError",
    "TransferError",
    "TransferSink",
    "TransferSinkLocal",
    "TransferSinkScp",
    "TransferSinkTus",
    "TransferSource",
    "TransferSourceHttp",
    "TransferSourceLocal",
    "TransferSourceSsh",
    "UploadInitiationError",
    "UploadOutcome",
    "UploadRestClient",
    "UploadTokenResult",
    "api_to_rest_url",
    "check_download_scope",
    "check_upload_scope",
    "collect_file_infos",
    "compute_file_info",
    "fetch_to_path",
    "http_source",
    "md5_checksum",
    "require_oauth",
    "require_scope",
    "require_tus",
    "resolve_paths",
    "resource_sources",
    "scp",
    "send_to_sink",
    "ssh_source",
    "token_provider",
    "tus_sink_for_resource",
]
