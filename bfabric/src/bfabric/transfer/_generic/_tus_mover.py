# tusclient (the ``tuspy`` package) ships no type information and is an OPTIONAL dependency (the
# ``[tus]`` extra), so it is unresolved when this package is typechecked without the extra. Disable
# the unknown-type family for this thin wrapper module only, rather than threading casts through
# every tuspy call.
# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
"""The tus resumable-upload mover.

Isolated in its own module because it is the ONLY place that imports ``tusclient`` (from the ``tuspy``
package, installed via the ``[tus]`` extra). Neither ``bfabric.transfer._generic.__init__`` nor
``bfabric.transfer._generic.send`` import this module at top level -- ``send_to_sink`` imports it lazily, only
when a tus sink is actually dispatched -- so a download-only / query install never pulls ``tuspy``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from tusclient.client import TusClient

from bfabric.transfer._generic._upload_types import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
    ProgressCallback,
    UploadOutcome,
    UrlCallback,
)
from bfabric.transfer._generic.errors import TransferError

if TYPE_CHECKING:
    from pathlib import Path


# RFC 6454 defines an origin using the scheme's default port when the URL omits one, so
# https://h and https://h:443 are the same origin. urlsplit().port is None in the implicit
# case, so compare an *effective* port to avoid spuriously rejecting a legitimate resume URL.
_DEFAULT_PORTS = {"http": 80, "https": 443}


def _same_origin(a: str, b: str) -> bool:
    """True if two URLs share scheme, host, and effective port (the scheme default if unspecified)."""
    ua, ub = urlsplit(a), urlsplit(b)
    pa = ua.port or _DEFAULT_PORTS.get(ua.scheme)
    pb = ub.port or _DEFAULT_PORTS.get(ub.scheme)
    return (ua.scheme, ua.hostname, pa) == (ub.scheme, ub.hostname, pb)


def upload_file(
    tus_endpoint: str,
    token: str,
    file_path: Path,
    metadata: dict[str, str],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    on_progress: ProgressCallback | None = None,
    resume_url: str | None = None,
    on_url: UrlCallback | None = None,
    retries: int = DEFAULT_RETRIES,
    retry_delay: int = DEFAULT_RETRY_DELAY,
) -> UploadOutcome:
    """Upload a single file using the tus protocol.

    Args:
        tus_endpoint: Base tus endpoint used to create a new upload.
        token: Bearer token for the Authorization header (the short-lived tus upload token).
        file_path: Local file to upload.
        metadata: tus metadata sent with the creation request.
        chunk_size: Bytes per PATCH request.
        on_progress: Called after each chunk with (bytes_done, total).
        resume_url: If given, resume a previously-started upload at this URL
            instead of creating a new one.
        on_url: Called once with the server-side upload URL as soon as it is
            known -- including when a fresh upload's first chunk fails after the
            creation request already registered the upload -- so the caller can
            always persist a URL to resume from.
        retries: Per-chunk retry attempts for transient network errors
            (tuspy resumes from the server offset on each retry).
        retry_delay: Seconds between retries.

    Returns:
        UploadOutcome on success. A transfer failure raises TransferError.

    Raises:
        ValueError: if ``resume_url`` does not share the origin (scheme/host/
            port) of ``tus_endpoint`` -- we refuse to send the bearer token to
            an unexpected host.
    """
    if resume_url is not None and not _same_origin(resume_url, tus_endpoint):
        raise ValueError(
            f"resume_url origin {urlsplit(resume_url).netloc!r} does not match "
            f"tus_endpoint origin {urlsplit(tus_endpoint).netloc!r}; refusing to "
            f"send the upload token to it."
        )

    client = TusClient(tus_endpoint)
    client.set_headers({"Authorization": f"Bearer {token}"})

    file_size = file_path.stat().st_size
    uploader = client.uploader(
        file_path=str(file_path),
        chunk_size=chunk_size,
        metadata=metadata,
        retries=retries,
        retry_delay=retry_delay,
    )

    start_offset = 0
    url_reported = False

    def _report_url(url: str | None) -> None:
        nonlocal url_reported
        if not url_reported and url:
            url_reported = True
            if on_url is not None:
                on_url(url)

    if resume_url is not None:
        # Resume: point at the existing upload and sync the local offset to
        # what the server already has. tuspy's set_url() does NOT sync the
        # uploader's offset, so without this the next PATCH is built from
        # offset 0 and the server rejects it with 409 (offset conflict).
        uploader.set_url(resume_url)
        try:
            # get_offset() issues a HEAD to the resume URL; a stale/unreachable
            # URL raises tuspy's TusCommunicationError, which is not a
            # TransferError -- wrap it so callers can catch TransferError.
            start_offset = uploader.get_offset()
        except Exception as exc:
            raise TransferError(f"failed to query resume offset for {file_path.name} from {resume_url}: {exc}") from exc
        uploader.offset = start_offset
        _report_url(resume_url)

    if file_size == 0:
        # tus still needs the creation request for a fresh empty file; a
        # resumed empty upload was already created, so skip it (and avoid a
        # second on_url call).
        if resume_url is None:
            uploader.upload()
            _report_url(uploader.url)
        if on_progress is not None:
            on_progress(0, 0)
        return UploadOutcome(bytes_uploaded=0, final_offset=0, upload_url=uploader.url or resume_url)

    if resume_url is not None and on_progress is not None:
        # Report the server-retained offset as the starting point.
        on_progress(start_offset, file_size)

    while uploader.offset < file_size:
        try:
            uploader.upload_chunk()
        except Exception as exc:
            raise TransferError(f"tus transfer failed for {file_path.name}: {exc}") from exc
        finally:
            # The creation POST sets uploader.url before the data PATCH, so the
            # URL exists even if the chunk failed -- report it either way.
            _report_url(uploader.url)
        if on_progress is not None:
            on_progress(uploader.offset, file_size)

    return UploadOutcome(
        bytes_uploaded=uploader.offset - start_offset,
        final_offset=uploader.offset,
        upload_url=uploader.url,
    )
