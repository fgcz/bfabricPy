from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from shutil import SameFileError
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from bfabric.transfer._generic.checksums import md5_checksum
from bfabric.transfer._generic.errors import TransferError
from bfabric.transfer._generic.scp import scp
from bfabric.transfer._generic.sources import (
    TransferSource,
    TransferSourceHttp,
    TransferSourceLocal,
    TransferSourceSsh,
)

if TYPE_CHECKING:
    from bfabric.transfer._generic.credentials import Credentials


def fetch_to_path(
    source: TransferSource,
    dest: Path,
    creds: Credentials,
    *,
    checksum: str | None = None,
    link_ok: bool = False,
) -> None:
    """Fetches ``source`` to ``dest`` using rsync/scp/cp/symlink or a streamed HTTP download.

    The download is atomic and checksum-verified where the transport allows. ``link_ok`` permits
    symlinking a local source in place of copying it. Raises :class:`TransferError` if the transfer
    ultimately fails.

    :param source: the file to fetch (a single transport-only source; candidate-list negotiation is
        deferred).
    :param dest: the full destination path (not a directory); parent directories are created.
    :param creds: credentials used for the transfer (ssh user, and the bearer-token provider for
        authenticated HTTP).
    :param checksum: expected MD5 hex digest to verify an HTTP download against, if available.
    :param link_ok: whether a local source may be symlinked instead of copied.
    """
    dest.parent.mkdir(exist_ok=True, parents=True)

    if isinstance(source, TransferSourceHttp):
        token = creds.token_provider() if creds.token_provider is not None else None
        success = _operation_copy_http(source=source, output_path=dest, checksum=checksum, bearer_token=token)
    elif not link_ok:
        success = _operation_copy_rsync(source, dest, creds.ssh_user)
        if not success:
            success = _operation_copy(source, dest, creds.ssh_user)
    else:
        # A remote source must never reach the symlink branch, which assumes a local path; callers
        # (and the binding) are expected to reject link_ok=True on a remote source before this point.
        if not isinstance(source, TransferSourceLocal):
            raise TransferError(f"Cannot link a non-local file: {source}")
        success = _operation_link_symbolic(source, dest)

    if not success:
        raise TransferError(f"Failed to fetch file: {source}")


def _operation_copy_rsync(
    source: TransferSourceSsh | TransferSourceLocal, output_path: Path, ssh_user: str | None
) -> bool:
    match source:
        case TransferSourceLocal(path=path):
            source_str = str(Path(path).resolve())
        case TransferSourceSsh(host=host, path=path):
            source_str = f"{ssh_user}@{host}:{path}" if ssh_user else f"{host}:{path}"
    # "--" terminates option parsing so a source/dest beginning with "-" can't be read as an rsync flag.
    cmd = ["rsync", "-rltvP", "--", source_str, str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def _operation_copy(source: TransferSourceSsh | TransferSourceLocal, output_path: Path, ssh_user: str | None) -> bool:
    match source:
        case TransferSourceLocal():
            return _operation_copy_cp(source, output_path)
        case TransferSourceSsh():
            return _operation_copy_scp(source, output_path, ssh_user)


def _operation_copy_http(
    source: TransferSourceHttp, output_path: Path, checksum: str | None, bearer_token: str | None
) -> bool:
    """Streams a file from an HTTP(S) URL to ``output_path``, verifying the checksum when available."""
    needs_auth = source.auth == "bfabric"

    if needs_auth and not bearer_token:
        raise TransferError(
            "HTTP resource access requires an OAuth-backed client (e.g. Bfabric.connect_pkce / connect_oauth) "
            "to provide a bearer token; the current credentials have none."
        )

    # Disable transport compression so the streamed bytes match the file the checksum was computed over.
    headers = {"Accept-Encoding": "identity"}
    # Only send the token for trusted, auth-required URLs; never leak it to arbitrary hosts.
    if needs_auth and bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    # Download to a temporary sibling and rename on success, so a mid-stream failure never leaves a
    # truncated file at output_path.
    tmp_path = output_path.with_name(f"{output_path.name}.part")
    logger.info(f"GET {source.url} -> {output_path}")
    try:
        with httpx.stream("GET", source.url, headers=headers, follow_redirects=True) as response:
            _ = response.raise_for_status()
            with tmp_path.open("wb") as fh:
                fh.writelines(response.iter_bytes())
    except httpx.HTTPError as error:
        tmp_path.unlink(missing_ok=True)
        detail = ""
        if isinstance(error, httpx.HTTPStatusError):
            code = error.response.status_code
            detail = f" (HTTP {code})"
            if code in (401, 403) and needs_auth:
                detail += "; the bearer token may be missing or lack the required 'containers' scope"
        logger.error(f"HTTP download failed for {source.url}{detail}: {error}")
        return False

    _verify_checksum(tmp_path, checksum, output_path)
    _ = tmp_path.replace(output_path)
    return True


def _verify_checksum(tmp_path: Path, expected: str | None, output_path: Path) -> None:
    """Verifies ``tmp_path`` against ``expected``, raising on mismatch; warns and skips if none was provided."""
    if expected is None:
        logger.warning(f"No checksum available for {output_path}; skipping integrity verification.")
        return
    actual_checksum = md5_checksum(tmp_path)
    if actual_checksum != expected:
        tmp_path.unlink(missing_ok=True)
        raise TransferError(
            f"Checksum mismatch for {output_path} (expected {expected}, got {actual_checksum});"
            " downloaded file is corrupt."
        )


def _operation_copy_scp(source: TransferSourceSsh, output_path: Path, ssh_user: str | None) -> bool:
    try:
        source_str = f"{source.host}:{source.path}"
        scp(source=source_str, target=output_path, user=ssh_user)
    except CalledProcessError:
        return False
    return True


def _operation_copy_cp(source: TransferSourceLocal, output_path: Path) -> bool:
    cmd = [str(Path(source.path).resolve()), str(output_path)]
    logger.info(shlex.join(["cp", *cmd]))
    try:
        _ = shutil.copyfile(*cmd)
    except (OSError, SameFileError):
        return False
    return True


def _operation_link_symbolic(source: TransferSourceLocal, output_path: Path) -> bool:
    # the link is created relative to the output file, so it should be more portable across apptainer images etc.
    # os.path.relpath (rather than Path.relative_to(..., walk_up=True), which is 3.12+) keeps this working on
    # the Python 3.11 the package supports while still walking up (emitting ``..``) when needed. Relativize
    # against output_path's own directory -- NOT output_path.resolve().parent, which would follow an already
    # present link to the source and yield the wrong (source-relative) target.
    source_abs = Path(source.path).resolve()
    source_path = Path(os.path.relpath(source_abs, output_path.parent.resolve()))

    # if the file exists, and only if it is a link as well
    if output_path.is_symlink():
        # Compare the link's real target to the source (both absolute). Resolving the *relative* target went
        # via the process CWD, so a correct link was only recognized when we happened to run from its own dir.
        if output_path.resolve() == source_abs:
            logger.info("Link already exists and points to the correct file")
            return True
        else:
            logger.info(f"rm {output_path}")
            output_path.unlink()
    elif output_path.exists():
        raise TransferError(f"Output path already exists and is not a symlink: {output_path}")
    cmd = ["ln", "-s", str(source_path), str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0
