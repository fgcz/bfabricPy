#!/usr/bin/env python3
"""Upload files from a delivery folder into a B-Fabric workunit storage folder.

This is a temporary crutch until a proper TUS upload server is available. It avoids the
base64 SOAP endpoint (Bfabric.upload_resource) and instead copies files directly on the
storage host, then registers each file as a B-Fabric resource.

Two execution contexts
----------------------
Omit ``--execute`` (default — dry-run)
    Validate the delivery folder, resolve the destination from the workunit id, and print
    what *would* happen. Read-only and safe for local/AI use with API credentials only.

Pass ``--execute``
    Copy each file into the workunit's storage folder, then register it as a B-Fabric
    resource.  This step must run as the ``bfabric`` unix user on the storage host:
    ``ssh -J fgcz-r-035.uzh.ch bfabric@localhost``
    The AI must never hold the bfabric unix credentials; a human runs this step.
"""
from __future__ import annotations

import getpass
import hashlib
import shutil
import stat as _stat
from pathlib import Path

import cyclopts
from loguru import logger

from bfabric import Bfabric
from bfabric.entities import Resource, Storage
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client

app = cyclopts.App(help=__doc__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_files(folder: Path) -> list[Path]:
    """Return all regular, non-hidden files under *folder* (recursively).

    Raises ``ValueError`` on the first symlink encountered (both file and
    directory symlinks are rejected — they break the path-safety guarantee).
    Hidden files and directories (names starting with ``.``) are skipped with
    a warning.
    """
    files: list[Path] = []
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not allowed in the delivery folder: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(folder)
        if any(part.startswith(".") for part in rel.parts):
            logger.warning(f"Skipping hidden path: {rel}")
            continue
        files.append(path)
    return files


def _validate_delivery_folder(folder: Path) -> list[Path]:
    """Validate *folder* and return the list of files to upload.

    Raises ``ValueError`` if the folder does not exist, is not a directory,
    or contains no regular files (after skipping hidden entries).
    """
    if not folder.exists():
        raise ValueError(f"Delivery folder does not exist: {folder}")
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")
    files = _collect_files(folder)
    if not files:
        raise ValueError(f"Delivery folder is empty (no files to upload): {folder}")
    return files


def _find_existing_resource_id(client: Bfabric, name: str, workunit_id: int) -> int | None:
    """Return the id of an existing resource with *name* in *workunit_id*, or ``None``."""
    result = client.reader.query_one(
        "resource",
        {"name": name, "workunitid": workunit_id},
        expected_type=Resource,
    )
    return result.id if result is not None else None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def upload_workunit_folder(
    workunit_id: int,
    folder: Path,
    execute: bool = False,
    update_existing: bool = False,
    *,
    client: Bfabric,
) -> None:
    """Validate *folder*, resolve the workunit destination, and copy+register files.

    :param workunit_id: Target workunit ID.
    :param folder: Prepared delivery folder whose contents are to be uploaded.
    :param execute: If ``True``, perform the actual copy and B-Fabric registration.
        Defaults to dry-run (read-only preview).
    :param update_existing: If ``True``, overwrite resources that are already
        registered for this workunit.  Defaults to ``False`` (skip with a warning).
    :param client: B-Fabric API client.
    """
    if execute and getpass.getuser() != "bfabric":
        logger.warning(
            f"Running --execute as user '{getpass.getuser()}' (not 'bfabric'). "
            "Files written to storage may not be accessible to B-Fabric's download layer."
        )

    files = _validate_delivery_folder(folder)
    total_size = sum(f.stat().st_size for f in files)
    logger.info(f"Delivery folder: {folder}  ({len(files)} file(s), {total_size:,} bytes)")

    workunit_definition = WorkunitDefinition.from_ref(workunit_id, client=client)
    registration = workunit_definition.registration
    if registration is None:
        raise ValueError(f"Workunit {workunit_id} has no registration information")

    storage = client.reader.query_one("storage", {"id": registration.storage_id}, expected_type=Storage)
    if storage is None:
        raise ValueError(f"Storage {registration.storage_id} not found")

    abs_dest = storage.base_path / registration.storage_output_folder
    logger.info(f"Destination folder: {abs_dest}")

    for local_path in files:
        relpath = local_path.relative_to(folder)
        dest_path = abs_dest / relpath
        rel_reg = registration.storage_output_folder / relpath
        file_size = local_path.stat().st_size

        existing_id = _find_existing_resource_id(client, local_path.name, registration.workunit_id)
        if existing_id is not None and not update_existing:
            logger.warning(
                f"  Skipping '{relpath}': resource already registered (id={existing_id}). "
                "Pass --update-existing to replace it."
            )
            continue

        if not execute:
            logger.info(f"  [DRY-RUN] copy  {relpath} -> {dest_path}")
            logger.info(
                f"  [DRY-RUN] save  resource  name={local_path.name!r}  "
                f"relativepath={str(rel_reg)!r}  size={file_size}  md5=[at execute]"
            )
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.copy(local_path, dest_path)
            # Use explicit 0o644; do NOT blindly propagate source mode bits — the B-Fabric
            # download layer expects owner-writable, group/other-readable files.
            dest_path.chmod(_stat.S_IRUSR | _stat.S_IWUSR | _stat.S_IRGRP | _stat.S_IROTH)
            with local_path.open("rb") as fh:
                checksum = hashlib.file_digest(fh, "md5").hexdigest()
            resource_data: dict[str, int | str] = {
                "name": local_path.name,
                "workunitid": registration.workunit_id,
                "storageid": registration.storage_id,
                "relativepath": str(rel_reg),
                "filechecksum": checksum,
                "status": "available",
                "size": file_size,
            }
            if existing_id is not None:
                resource_data["id"] = existing_id
            _ = client.save("resource", resource_data)
            logger.info(f"  Copied and registered: {relpath}")

    if not execute:
        logger.info(
            "Dry-run complete — no files written, no resources registered.\n"
            "Pass --execute to perform the upload "
            "(run as the bfabric unix user on the storage host)."
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@app.default
@use_client
def main(
    workunit_id: int,
    folder: Path,
    *,
    execute: bool = False,
    update_existing: bool = False,
    client: Bfabric,
) -> None:
    """Upload files from a prepared delivery folder into a B-Fabric workunit storage folder.

    :param workunit_id: Target workunit ID.
    :param folder: Prepared delivery folder whose contents are to be uploaded.
    :param execute: Perform the actual copy + registration.  Default is dry-run (read-only).
    :param update_existing: Overwrite resources already registered for this workunit.
    :param client: B-Fabric API client (injected by @use_client).
    """
    upload_workunit_folder(
        workunit_id=workunit_id,
        folder=folder,
        execute=execute,
        update_existing=update_existing,
        client=client,
    )


if __name__ == "__main__":
    app()
