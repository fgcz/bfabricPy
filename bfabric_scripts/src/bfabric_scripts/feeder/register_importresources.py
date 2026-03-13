from __future__ import annotations

from enum import Enum
import os
import time
import sqlite3

import textwrap

from loguru import logger

from bfabric import Bfabric, BfabricClientConfig

from pydantic import BaseModel


# TODO the application_mapping module provides now ,he most essential information to perform the registration
# #  but the filename parsing needs to hack the "Metabolomics/Biohpysics" ambiguity still
#


class RegistrationStatus(Enum):
    registered = 1
    pending = 2
    failed_unknown_error = 3
    failed_deterministic = 4
    failed_unknown_application = 5


class ImportResourcesDB:
    """Database handler for import resources registration."""

    def __init__(self, db_path: str):
        """
        Initialize database connection and create schema if needed.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_schema()
        self._enable_wal_mode()

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    _SCHEMA = textwrap.dedent(
        """
        CREATE TABLE IF NOT EXISTS import_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            file_size INT NOT NULL,
            file_unix_timestamp INT NOT NULL,
            md5_checksum TEXT NOT NULL,
            registration_status INT NOT NULL,
            status_updated_at INT NOT NULL
        );

        -- fast look up
        CREATE INDEX IF NOT EXISTS import_resources_file_path_idx ON import_resources (file_path);
    """
    )

    def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        with self.conn:
            self.conn.executescript(self._SCHEMA)

    def _enable_wal_mode(self) -> None:
        """Enable Write-Ahead Logging mode for better concurrency."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        self.conn.commit()

    def is_registered(self, file_path: str) -> bool:
        """
        Check if a file path is already registered.

        Args:
            file_path: Path to check

        Returns:
            True if file is already registered, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM import_resources WHERE file_path = ?", (file_path,))
        return cursor.fetchone() is not None

    def get_unregistered(self, entries: list) -> list:
        """
        Filter out entries that are already registered.

        Args:
            entries: List of entry dictionaries

        Returns:
            List of entries that are not yet registered
        """
        return [entry for entry in entries if not self.is_registered(entry["file_path"])]

    def insert_pending(self, entry: dict) -> int:
        """
        Insert an entry with pending status.

        Args:
            entry: Entry dictionary with file information

        Returns:
            The ID of the inserted entry
        """
        cursor = self.conn.cursor()
        current_time = int(time.time())

        cursor.execute(
            """INSERT INTO import_resources
               (file_path, file_size, file_unix_timestamp, md5_checksum, registration_status, status_updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                entry["file_path"],
                entry["file_size"],
                entry["file_unix_timestamp"],
                entry["md5_checksum"],
                RegistrationStatus.pending.value,
                current_time,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_status(self, entry_id: int, status: RegistrationStatus) -> None:
        """
        Update the registration status of an entry.

        Args:
            entry_id: ID of the entry to update
            status: New registration status
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE import_resources SET registration_status = ?, status_updated_at = ? WHERE id = ?",
            (status.value, int(time.time()), entry_id),
        )
        self.conn.commit()

    def update_status_by_path(self, file_path: str, status: RegistrationStatus) -> None:
        """
        Update the registration status of an entry by file path.

        Args:
            file_path: Path of the entry to update
            status: New registration status
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE import_resources SET registration_status = ?, status_updated_at = ? WHERE file_path = ?",
            (status.value, int(time.time()), file_path),
        )
        self.conn.commit()


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


def create_importresource_dict(
    config: BfabricClientConfig,
    feeder_config: FeederConfig,
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


def _get_sample_id_from_path(file_path: str) -> int | None:
    """
    Extract sample ID from file path.

    TODO: Implement proper logic to extract sample ID from file path.

    Args:
        file_path: Path to the file

    Returns:
        Sample ID if found, None otherwise
    """
    # TODO: Implement proper parsing logic
    # This is a placeholder that returns None

    logger.debug(f"Placeholder: No sample ID extracted from {file_path}")

    return None
