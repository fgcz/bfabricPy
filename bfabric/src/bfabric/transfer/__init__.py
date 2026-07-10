"""The B-Fabric transfer layer: transport-agnostic byte movers.

This first slice ships only the generic movers (:mod:`bfabric.transfer._generic`) -- transport-only
source/sink value objects, ``Credentials``, ``fetch_to_path`` (download) and ``send_to_sink``
(upload, tus behind the ``[transfer]`` extra). They know nothing about B-Fabric and are re-exported
here for convenience. The B-Fabric domain binding (the ``/rest/upload/*`` client, token acquisition,
Resource -> source mapping) lands in a follow-up and will extend these exports.

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

__all__ = [
    "Credentials",
    "FileInfo",
    "TransferError",
    "TransferSink",
    "TransferSinkLocal",
    "TransferSinkScp",
    "TransferSinkTus",
    "TransferSource",
    "TransferSourceHttp",
    "TransferSourceLocal",
    "TransferSourceSsh",
    "UploadOutcome",
    "collect_file_infos",
    "compute_file_info",
    "fetch_to_path",
    "md5_checksum",
    "resolve_paths",
    "scp",
    "send_to_sink",
]
