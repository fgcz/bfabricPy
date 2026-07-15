from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

ProgressCallback = Callable[[int, int], None]
"""Called with (bytes_done, total) after each chunk. bytes_done is absolute."""

UrlCallback = Callable[[str], None]
"""Called once with the server-side upload URL as soon as it is known."""

DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 5


@dataclass
class UploadOutcome:
    """Result of a single successful file transfer to a sink.

    ``bytes_uploaded`` is the number of bytes actually sent during *this* call, whereas
    ``final_offset`` is the absolute offset confirmed on the server (the total size now stored). For a
    fresh upload the two are equal; for a resumed tus upload ``final_offset`` also counts the bytes a
    previous session already delivered, so ``final_offset >= bytes_uploaded``. For non-resumable sinks
    (local/scp) both equal the file size.

    ``upload_url`` is the server-side (resumable) upload URL for a tus transfer; persist it (via the
    ``on_url`` callback, which fires as soon as the URL exists -- even if the transfer then fails) to
    resume a later interrupted transfer via ``send_to_sink(..., resume_url=...)``. It is ``None`` for
    non-resumable sinks (local/scp). A failed transfer raises
    :class:`~bfabric.transfer._generic.errors.TransferError` rather than returning.
    """

    bytes_uploaded: int
    final_offset: int
    upload_url: str | None


# These types are deliberately kept in a module that does NOT import ``tusclient``, so that
# ``bfabric.transfer._generic.__init__`` and ``bfabric.transfer._generic.send`` can re-export ``UploadOutcome`` without
# dragging ``tuspy`` into a download-only / query install.
