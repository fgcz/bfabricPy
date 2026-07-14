"""Transport-agnostic file movers for B-Fabric resource I/O.

This package moves bytes given a transport-only source/sink description plus credentials. It knows
nothing about B-Fabric: the domain binding (Resource -> source/sink, token acquisition) lives in
core ``bfabric.transfer``. Base install needs only ``httpx``; the tus resumable-upload mover is
gated behind the ``[transfer]`` extra and is imported lazily, so a download-only consumer never pulls
``tuspy``.
"""

from __future__ import annotations

from bfabric.transfer._generic._upload_types import UploadOutcome
from bfabric.transfer._generic.checksums import (
    FileInfo,
    collect_file_infos,
    compute_file_info,
    md5_checksum,
)
from bfabric.transfer._generic.credentials import Credentials
from bfabric.transfer._generic.errors import TransferError
from bfabric.transfer._generic.fetch import fetch_to_path
from bfabric.transfer._generic.scp import scp
from bfabric.transfer._generic.send import send_to_sink
from bfabric.transfer._generic.sinks import (
    TransferSink,
    TransferSinkLocal,
    TransferSinkScp,
    TransferSinkTus,
)
from bfabric.transfer._generic.sources import (
    TransferSource,
    TransferSourceHttp,
    TransferSourceLocal,
    TransferSourceSsh,
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
    "scp",
    "send_to_sink",
]
