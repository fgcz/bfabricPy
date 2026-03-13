from __future__ import annotations
import time
from enum import Enum
import sqlite3
import textwrap
from typing import List, Dict, Any

from loguru import logger


class RegistrationStatus(Enum):
    registered = 1
    pending = 2
    failed_unknown_error = 3
    failed_deterministic = 4
    failed_unknown_application = 5


# Safe batch size for queries
_CHUNK_SIZE = 100


class ImportResourcesDB:
    """Database handler for import resources registration."""

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

        CREATE INDEX IF NOT EXISTS import_resources_file_path_idx
        ON import_resources (file_path);
    """
    )

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._initialize()

    def close(self) -> None:
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _initialize(self) -> None:
        """Create schema and enable WAL mode."""
        with self.conn:
            self.conn.executescript(self._SCHEMA)
            self.conn.execute("PRAGMA journal_mode=WAL")

    def is_registered(self, file_path: str) -> bool:
        """Check if a file path is already registered."""
        cursor = self.conn.execute("SELECT 1 FROM import_resources WHERE file_path = ? LIMIT 1", (file_path,))
        return cursor.fetchone() is not None

    def get_unregistered(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out entries that are already registered.

        Processes entries in chunks of 100 to ensure queries remain lightweight.
        """
        if not entries:
            return []

        # 1. Extract just the file paths
        file_paths = [entry["file_path"] for entry in entries]
        registered_paths = set()

        # 2. Loop through the list in chunks of 100
        for i in range(0, len(file_paths), _CHUNK_SIZE):
            chunk = file_paths[i : i + _CHUNK_SIZE]

            # Create placeholders like (?,?,?...) for this chunk
            placeholders = ",".join("?" for _ in chunk)

            # Query DB for this specific chunk
            query = f"SELECT file_path FROM import_resources WHERE file_path IN ({placeholders})"
            cursor = self.conn.execute(query, chunk)

            # Store results in a set for fast lookup
            for row in cursor:
                registered_paths.add(row[0])

        # 3. Filter the original list based on our gathered set
        return [entry for entry in entries if entry["file_path"] not in registered_paths]

    def insert_pending(self, entry: Dict[str, Any]) -> int:
        """Insert an entry with pending status."""
        current_time = int(time.time())

        with self.conn:
            cursor = self.conn.execute(
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
            return cursor.lastrowid

    def _update_status(self, identifier_column: str, identifier_value: str | int, status: RegistrationStatus) -> None:
        """Internal helper to update status by ID or Path."""
        current_time = int(time.time())
        with self.conn:
            self.conn.execute(
                f"UPDATE import_resources SET registration_status = ?, status_updated_at = ? WHERE {identifier_column} = ?",
                (status.value, current_time, identifier_value),
            )

    def update_status(self, entry_id: int, status: RegistrationStatus) -> None:
        """Update the registration status of an entry by ID."""
        self._update_status("id", entry_id, status)

    def update_status_by_path(self, file_path: str, status: RegistrationStatus) -> None:
        """Update the registration status of an entry by file path."""
        self._update_status("file_path", file_path, status)
