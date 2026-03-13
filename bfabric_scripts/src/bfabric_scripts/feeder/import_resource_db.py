from __future__ import annotations
import time
from enum import Enum
import sqlite3
import textwrap

from loguru import logger


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
