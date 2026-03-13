from __future__ import annotations

import os
import re
import time
from pathlib import Path

import polars as pl
from bfabric import Bfabric
from bfabric_scripts.feeder.application_mapping import SystemConfig
from bfabric_scripts.feeder.import_resource_db import ImportResourcesDB, RegistrationStatus
from bfabric_scripts.feeder.path_convention_compms import PathConventionCompMS
from loguru import logger


class UnknownApplicationError(Exception):
    """Raised when a file's application name is not found in the mapping."""

    def __init__(self, application_name: str, file_path: str) -> None:
        super().__init__(f"Unknown application '{application_name}' for path: {file_path}")
        self.application_name = application_name
        self.file_path = file_path


def _get_sample_id_from_path(file_path: str) -> int | None:
    """Returns the sample id for a given file path, if it's present in the correct format."""
    match = re.search(
        r"p\d+/(?:Proteomics|Metabolomics)/[A-Z]+_[1-9]/.*_\d{3}(?:_C\d+)?_S(?P<S>\d{6,})_.*\.(?:raw|zip)$",
        file_path,
    )
    if match:
        sample_id = match.group("S")
        logger.info(f"found sample_id={sample_id} in path={file_path}")
        return int(sample_id)


def _get_bfabric_application_and_project_id(
    app_mapping: pl.DataFrame,
    path_convention: PathConventionCompMS,
    file_path: str,
) -> tuple[int, int]:
    parsed = path_convention.parse_relative_path(Path(file_path))
    matching = app_mapping.filter(pl.col("application_name") == parsed.application_name)
    if matching.is_empty():
        raise UnknownApplicationError(parsed.application_name, file_path)
    return int(matching["application_id"][0]), parsed.container_id


def create_importresource_dict(
    app_mapping: pl.DataFrame,
    path_convention: PathConventionCompMS,
    feeder_config: SystemConfig,
    file_path: str,
    file_size: int,
    file_unix_timestamp: int,
    md5_checksum: str,
) -> dict[str, str | int]:
    """
    Create a dictionary for bfabric importresource registration.

    :param app_mapping: Application mapping DataFrame (from application_mapping module)
    :param path_convention: Path convention parser for the storage
    :param feeder_config: Feeder system configuration
    :param file_path: Relative path to the file
    :param file_size: Size of the file in bytes
    :param file_unix_timestamp: Unix timestamp of the file
    :param md5_checksum: MD5 checksum of the file
    :raises UnknownApplicationError: If the application name parsed from the path is not in the mapping
    """
    file_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(file_unix_timestamp))
    application_id, project_id = _get_bfabric_application_and_project_id(app_mapping, path_convention, file_path)
    obj: dict[str, str | int] = {
        "applicationid": application_id,
        "filechecksum": md5_checksum,
        "containerid": project_id,
        "filedate": file_date,
        "relativepath": file_path,
        "name": os.path.basename(file_path),
        "size": file_size,
        "storageid": feeder_config.storage_id,
    }
    sample_id = _get_sample_id_from_path(file_path)
    if sample_id is not None:
        obj["sampleid"] = sample_id
    return obj


def _register_with_bfabric(
    entry: dict,
    bfabric_client: Bfabric,
    app_mapping: pl.DataFrame,
    path_convention: PathConventionCompMS,
    feeder_config: SystemConfig,
) -> None:
    obj = create_importresource_dict(
        app_mapping=app_mapping,
        path_convention=path_convention,
        feeder_config=feeder_config,
        file_path=entry["file_path"],
        file_size=entry["file_size"],
        file_unix_timestamp=entry["file_unix_timestamp"],
        md5_checksum=entry["md5_checksum"],
    )
    bfabric_client.save(endpoint="importresource", obj=obj)


def _process_entry(
    entry: dict,
    db: ImportResourcesDB,
    bfabric_client: Bfabric,
    app_mapping: pl.DataFrame,
    path_convention: PathConventionCompMS,
    feeder_config: SystemConfig,
) -> None:
    try:
        entry_id = db.insert_pending(entry)
    except Exception as e:
        logger.error(f"Failed to insert pending entry for {entry['file_path']}: {e}")
        return

    try:
        _register_with_bfabric(entry, bfabric_client, app_mapping, path_convention, feeder_config)
        db.update_status(entry_id, RegistrationStatus.registered)
        logger.info(f"Successfully registered: {entry['file_path']}")
    except UnknownApplicationError as e:
        db.update_status(entry_id, RegistrationStatus.failed_unknown_application)
        logger.warning(f"Unknown application for {entry['file_path']}: {e}")
    except Exception as e:
        db.update_status(entry_id, RegistrationStatus.failed_unknown_error)
        logger.error(f"Failed to register {entry['file_path']}: {e}")


def register_import_resources(
    entries: list,
    db_path: str,
    bfabric_client: Bfabric,
    app_mapping: pl.DataFrame,
    path_convention: PathConventionCompMS,
    feeder_config: SystemConfig,
) -> None:
    """
    Register import resources in bfabric.

    :param entries: List of dicts with keys: file_path, file_size, file_unix_timestamp, md5_checksum
    :param db_path: Path to the SQLite tracking database
    :param bfabric_client: Bfabric client for API calls
    :param app_mapping: Application mapping DataFrame (from application_mapping module)
    :param path_convention: Path convention parser for the storage
    :param feeder_config: Feeder system configuration
    """
    if not entries:
        logger.info("No entries to process")
        return

    with ImportResourcesDB(db_path) as db:
        entries_to_process = db.get_unregistered(entries)
        logger.info(f"Found {len(entries_to_process)} new entries to process (out of {len(entries)} total)")
        for entry in entries_to_process:
            _process_entry(entry, db, bfabric_client, app_mapping, path_convention, feeder_config)
