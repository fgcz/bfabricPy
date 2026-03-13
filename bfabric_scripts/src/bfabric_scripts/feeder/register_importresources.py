from __future__ import annotations

import os
import re
import time

from bfabric import Bfabric, BfabricClientConfig
from bfabric_scripts.feeder.application_mapping import SystemConfig
from bfabric_scripts.feeder.import_resource_db import ImportResourcesDB, RegistrationStatus
from loguru import logger

from pydantic import BaseModel


# TODO the application_mapping module provides now ,he most essential information to perform the registration
# #  but the filename parsing needs to hack the "Metabolomics/Biohpysics" ambiguity still
#


def _process_entry(entry: dict, db: ImportResourcesDB, bfabric_client: Bfabric | None = None) -> None:
    """
    Process a single entry: insert as pending, register, and update status.

    Args:
        entry: Entry dictionary with file information
        db: ImportResourcesDB instance
        bfabric_client: Optional Bfabric client for registration
    """
    try:
        entry_id = db.insert_pending(entry)

        registration_success = _register_with_bfabric_placeholder(entry, bfabric_client)

        if registration_success:
            db.update_status(entry_id, RegistrationStatus.registered)
            logger.info(f"Successfully registered: {entry['file_path']}")
        else:
            db.update_status(entry_id, RegistrationStatus.failed_unknown_error)
            logger.warning(f"Failed to register: {entry['file_path']}")

    except Exception as e:
        logger.error(f"Error processing entry {entry['file_path']}: {e}")
        db.update_status_by_path(entry["file_path"], RegistrationStatus.failed_unknown_error)


def register_import_resources(entries: list, db_path: str, bfabric_client: Bfabric | None = None) -> None:
    """
    Register import resources in bfabric.

    Args:
        entries: List of dictionaries containing file information (keys: file_path, file_size, file_unix_timestamp, md5_checksum)
        db_path: Path to the SQLite database file
        bfabric_client: Optional Bfabric client for registration
    """
    if not entries:
        logger.info("No entries to process")
        return

    db = ImportResourcesDB(db_path)

    try:
        entries_to_process = db.get_unregistered(entries)
        logger.info(f"Found {len(entries_to_process)} new entries to process (out of {len(entries)} total)")

        if not entries_to_process:
            return

        for entry in entries_to_process:
            _process_entry(entry, db, bfabric_client)

    finally:
        db.close()


def _register_with_bfabric_placeholder(entry: dict, bfabric_client: Bfabric | None) -> bool:
    """
    Placeholder function for registering files with bfabric.

    TODO: Implement actual bfabric registration logic here.

    Args:
        entry: Dictionary containing file information
        bfabric_client: Optional Bfabric client

    Returns:
        bool: True if registration successful, False otherwise
    """
    logger.info(f"Placeholder: Would register {entry['file_path']} with bfabric")
    logger.debug(f"Entry details: {entry}")

    # TODO: Replace with actual bfabric registration logic
    # Example of what this might look like:
    # if bfabric_client:
    #     try:
    #         bfabric_client.save(endpoint="importresource", obj={...})
    #         return True
    #     except Exception as e:
    #         logger.error(f"Bfabric registration failed: {e}")
    #         return False

    # For now, return True as a placeholder
    return True


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


def create_importresource_dict(
    config: BfabricClientConfig,
    feeder_config: SystemConfig,
    file_path: str,
    file_size: int,
    file_unix_timestamp: int,
    md5_checksum: str,
) -> dict[str, str | int]:
    """
    Create a dictionary for bfabric importresource registration.

    Args:
        config: Bfabric client configuration
        feeder_config: Feeder configuration
        file_path: Path to the file
        file_size: Size of the file in bytes
        file_unix_timestamp: Unix timestamp of the file
        md5_checksum: MD5 checksum of the file

    Returns:
        Dictionary with keys required for bfabric importresource registration
    """
    # Format the timestamp for bfabric
    file_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(file_unix_timestamp))
    bfabric_application_ids = config.application_ids
    if not bfabric_application_ids:
        raise RuntimeError("No bfabric_application_ids configured. check '~/.bfabricpy.yml' file!")
    bfabric_application_id, bfabric_projectid = _get_bfabric_application_and_project_id(
        bfabric_application_ids, file_path
    )
    obj = {
        "applicationid": bfabric_application_id,
        "filechecksum": md5_checksum,
        "containerid": bfabric_projectid,
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


def _get_bfabric_application_and_project_id(application_ids: dict, file_path: str) -> tuple[int, int]:
    """
    Get bfabric application ID and project ID from file path.

    TODO: Implement proper logic to parse file path and determine application/project IDs.

    Args:
        application_ids: Dictionary of application IDs from config
        file_path: Path to the file

    Returns:
        Tuple of (application_id, project_id)
    """
    # TODO: Implement proper parsing logic based on file path structure
    # This is a placeholder that returns default values

    # For now, return the first application ID and a default project ID
    first_app_id = list(application_ids.values())[0]
    default_project_id = 1

    logger.debug(f"Placeholder: Using app_id={first_app_id}, project_id={default_project_id} for {file_path}")

    return first_app_id, default_project_id
