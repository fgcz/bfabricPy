from __future__ import annotations

import shutil
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

from loguru import logger

from bfabric.transfer._generic._upload_types import ProgressCallback, UploadOutcome, UrlCallback
from bfabric.transfer._generic.errors import TransferError
from bfabric.transfer._generic.scp import scp
from bfabric.transfer._generic.sinks import (
    TransferSink,
    TransferSinkLocal,
    TransferSinkScp,
    TransferSinkTus,
)

if TYPE_CHECKING:
    from pathlib import Path

    from bfabric.transfer._generic.credentials import Credentials


def send_to_sink(
    sink: TransferSink,
    src: Path,
    creds: Credentials,
    *,
    on_progress: ProgressCallback | None = None,
    resume_url: str | None = None,
    on_url: UrlCallback | None = None,
) -> UploadOutcome:
    """Pushes the bytes of ``src`` to ``sink``.

    A tus sink is resumable: capture its URL via ``on_url`` and pass it back as ``resume_url`` to
    resume an interrupted transfer. scp and local copies are not resumable, so ``resume_url`` /
    ``on_url`` are ignored for them and the returned ``UploadOutcome.upload_url`` is ``None``. Raises
    :class:`~bfabric.transfer._generic.errors.TransferError` on failure.
    """
    match sink:
        case TransferSinkLocal():
            return _send_local(sink, src, on_progress)
        case TransferSinkScp():
            return _send_scp(sink, src, creds, on_progress)
        case TransferSinkTus():
            # tuspy is optional (the bfabric[transfer] extra). _tus_mover imports tusclient at module
            # top, so it is imported here -- only when a tus sink is actually dispatched -- keeping a
            # base / download-only / query install free of tuspy. A missing extra surfaces as a clear
            # TransferError rather than a bare ModuleNotFoundError.
            try:
                from bfabric.transfer._generic._tus_mover import upload_file
            except ImportError as exc:
                raise TransferError(
                    "tus uploads require the optional 'tuspy' dependency; install bfabric[transfer]."
                ) from exc

            return upload_file(
                sink.endpoint,
                sink.token.get_secret_value(),
                src,
                sink.metadata,
                on_progress=on_progress,
                resume_url=resume_url,
                on_url=on_url,
            )


def _send_local(sink: TransferSinkLocal, src: Path, on_progress: ProgressCallback | None) -> UploadOutcome:
    size = src.stat().st_size
    sink.path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"cp {src} {sink.path}")
    try:
        _ = shutil.copyfile(src, sink.path)
    except OSError as exc:
        raise TransferError(f"failed to copy {src} to {sink.path}: {exc}") from exc
    if on_progress is not None:
        on_progress(size, size)
    return UploadOutcome(bytes_uploaded=size, final_offset=size, upload_url=None)


def _send_scp(
    sink: TransferSinkScp, src: Path, creds: Credentials, on_progress: ProgressCallback | None
) -> UploadOutcome:
    size = src.stat().st_size
    target = f"{sink.host}:{sink.path}"
    try:
        scp(source=src, target=target, user=creds.ssh_user)
    except CalledProcessError as exc:
        raise TransferError(f"scp of {src} to {target} failed: {exc}") from exc
    if on_progress is not None:
        on_progress(size, size)
    return UploadOutcome(bytes_uploaded=size, final_offset=size, upload_url=None)
