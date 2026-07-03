import shlex
import shutil
import subprocess
from pathlib import Path
from shutil import SameFileError
from subprocess import CalledProcessError

import httpx
from loguru import logger

from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile
from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceHttp,
    FileSourceLocal,
    FileSourceSsh,
    FileSourceSshValue,
)
from bfabric_app_runner.util.checksum import md5_checksum
from bfabric_app_runner.util.scp import scp


def prepare_resolved_file(file: ResolvedFile, working_dir: Path, context: PrepareContext) -> None:
    """Prepares the file specified by the spec."""
    output_path = working_dir / file.filename
    output_path.parent.mkdir(exist_ok=True, parents=True)

    if isinstance(file.source, FileSourceHttp):
        success = _operation_copy_http(
            source=file.source, output_path=output_path, checksum=file.checksum, bearer_token=context.bearer_token
        )
    elif not file.link:
        success = _operation_copy_rsync(file.source, output_path, context.ssh_user)
        if not success:
            success = _operation_copy(file.source, output_path, context.ssh_user)
    else:
        # FileSpec.validate_no_link_remote rejects link=True with a non-local source before resolution,
        # so reaching here with a remote source would mean that invariant broke upstream.
        if not isinstance(file.source, FileSourceLocal):
            raise RuntimeError(f"Cannot link a non-local file: {file}")
        success = _operation_link_symbolic(file.source, output_path)
    if not success:
        raise RuntimeError(f"Failed to copy file: {file}")


def _operation_copy_rsync(source: FileSourceSsh | FileSourceLocal, output_path: Path, ssh_user: str | None) -> bool:
    match source:
        case FileSourceLocal(local=local):
            source_str = str(Path(local).resolve())
        case FileSourceSsh(ssh=FileSourceSshValue(host=host, path=path)):
            source_str = f"{ssh_user}@{host}:{path}" if ssh_user else f"{host}:{path}"
    cmd = ["rsync", "-rltvP", source_str, str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def _operation_copy(source: FileSourceSsh | FileSourceLocal, output_path: Path, ssh_user: str | None) -> bool:
    match source:
        case FileSourceLocal():
            return _operation_copy_cp(source, output_path)
        case FileSourceSsh():
            return _operation_copy_scp(source, output_path, ssh_user)


def _operation_copy_http(
    source: FileSourceHttp, output_path: Path, checksum: str | None, bearer_token: str | None
) -> bool:
    """Streams a file from an HTTP(S) URL to ``output_path``, verifying the checksum when available."""
    http = source.http
    needs_auth = http.auth == "bfabric"

    if needs_auth and not bearer_token:
        raise RuntimeError(
            "HTTP resource access requires an OAuth-backed client (e.g. Bfabric.connect_pkce / connect_oauth) "
            "to provide a bearer token; the current client has none. Use access: ssh, or connect via OAuth."
        )

    # Disable transport compression so the streamed bytes match the file the checksum was computed over.
    headers = {"Accept-Encoding": "identity"}
    # Only send the token for trusted, auth-required URLs; never leak it to arbitrary hosts.
    if needs_auth and bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    # Download to a temporary sibling and rename on success, so a mid-stream failure never leaves a
    # truncated file at output_path.
    tmp_path = output_path.with_name(f"{output_path.name}.part")
    logger.info(f"GET {http.url} -> {output_path}")
    try:
        with httpx.stream("GET", http.url, headers=headers, follow_redirects=True) as response:
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
        logger.error(f"HTTP download failed for {http.url}{detail}: {error}")
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
        raise RuntimeError(
            f"Checksum mismatch for {output_path} (expected {expected}, got {actual_checksum});"
            " downloaded file is corrupt."
        )


def _operation_copy_scp(source: FileSourceSsh, output_path: Path, ssh_user: str | None) -> bool:
    try:
        source_str = f"{source.ssh.host}:{source.ssh.path}"
        scp(source=source_str, target=output_path, user=ssh_user)
    except CalledProcessError:
        return False
    return True


def _operation_copy_cp(source: FileSourceLocal, output_path: Path) -> bool:
    cmd = [str(Path(source.local).resolve()), str(output_path)]
    logger.info(shlex.join(["cp", *cmd]))
    try:
        shutil.copyfile(*cmd)
    except (OSError, SameFileError):
        return False
    return True


def _operation_link_symbolic(source: FileSourceLocal, output_path: Path) -> bool:
    # the link is created relative to the output file, so it should be more portable across apptainer images etc
    source_path = Path(source.local).resolve().relative_to(output_path.resolve().parent, walk_up=True)

    # if the file exists, and only if it is a link as well
    if output_path.is_symlink():
        # check if it points to the same file, in which case we don't need to do anything
        if output_path.resolve() == source_path.resolve():
            logger.info("Link already exists and points to the correct file")
            return True
        else:
            logger.info(f"rm {output_path}")
            output_path.unlink()
    elif output_path.exists():
        raise RuntimeError(f"Output path already exists and is not a symlink: {output_path}")
    cmd = ["ln", "-s", str(source_path), str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0
