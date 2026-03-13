import time
from pathlib import Path

import pytest

from bfabric_scripts.feeder.import_resource_db import (
    ImportResourcesDB,
    RegistrationStatus,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture to provide a database file path in the tmp_path directory."""
    return tmp_path / "test_import_resources.db"


@pytest.fixture
def db(db_path: Path) -> ImportResourcesDB:
    """Fixture to provide an ImportResourcesDB instance with automatic cleanup."""
    db_instance = ImportResourcesDB(str(db_path))
    yield db_instance
    db_instance.close()


def create_test_entry(
    file_path: str,
    file_size: int = 1024,
    file_unix_timestamp: int = int(time.time()),
    md5_checksum: str = "abc123def456",
) -> dict:
    """Helper function to create a test entry dictionary."""
    return {
        "file_path": file_path,
        "file_size": file_size,
        "file_unix_timestamp": file_unix_timestamp,
        "md5_checksum": md5_checksum,
    }


def test_database_initialization(db_path: Path) -> None:
    """Test that database is properly initialized with schema."""
    db = ImportResourcesDB(str(db_path))

    try:
        # Verify that the database file was created
        assert db_path.exists()

        # Verify that the table exists
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='import_resources'")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "import_resources"

        # Verify that the index exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='import_resources_file_path_idx'")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "import_resources_file_path_idx"

    finally:
        db.close()


def test_wal_mode_enabled(db: ImportResourcesDB) -> None:
    """Test that WAL mode is enabled."""
    cursor = db.conn.cursor()
    cursor.execute("PRAGMA journal_mode")
    result = cursor.fetchone()
    assert result[0] == "wal"


def test_insert_pending(db: ImportResourcesDB) -> None:
    """Test inserting an entry with pending status."""
    entry = create_test_entry("test/file1.txt")

    entry_id = db.insert_pending(entry)

    # Verify that the entry was inserted
    assert entry_id > 0

    # Verify that the entry exists in the database
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM import_resources WHERE id = ?", (entry_id,))
    result = cursor.fetchone()
    assert result is not None

    # Verify the values
    assert result[1] == "test/file1.txt"  # file_path
    assert result[2] == 1024  # file_size
    assert result[3] == entry["file_unix_timestamp"]  # file_unix_timestamp
    assert result[4] == "abc123def456"  # md5_checksum
    assert result[5] == RegistrationStatus.pending.value  # registration_status


def test_is_registered(db: ImportResourcesDB) -> None:
    """Test checking if a file path is registered."""
    entry = create_test_entry("test/file2.txt")

    # Before insertion
    assert not db.is_registered("test/file2.txt")

    # Insert the entry
    db.insert_pending(entry)

    # After insertion
    assert db.is_registered("test/file2.txt")


def test_get_unregistered(db: ImportResourcesDB) -> None:
    """Test filtering out already registered entries."""
    # Insert some entries
    entry1 = create_test_entry("test/file1.txt")
    entry2 = create_test_entry("test/file2.txt")
    entry3 = create_test_entry("test/file3.txt")

    db.insert_pending(entry1)
    db.insert_pending(entry2)

    # Create a list of entries
    entries = [
        entry1,  # Already registered
        entry2,  # Already registered
        entry3,  # Not registered
    ]

    # Filter unregistered
    unregistered = db.get_unregistered(entries)

    # Verify the result
    assert len(unregistered) == 1
    assert unregistered[0]["file_path"] == "test/file3.txt"


def test_update_status(db: ImportResourcesDB) -> None:
    """Test updating the status of an entry by ID."""
    entry = create_test_entry("test/file4.txt")
    entry_id = db.insert_pending(entry)

    # Update the status to registered
    db.update_status(entry_id, RegistrationStatus.registered)

    # Verify the update
    cursor = db.conn.cursor()
    cursor.execute("SELECT registration_status FROM import_resources WHERE id = ?", (entry_id,))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == RegistrationStatus.registered.value


def test_update_status_by_path(db: ImportResourcesDB) -> None:
    """Test updating the status of an entry by file path."""
    entry = create_test_entry("test/file5.txt")
    db.insert_pending(entry)

    # Update the status by path
    db.update_status_by_path("test/file5.txt", RegistrationStatus.failed_unknown_error)

    # Verify the update
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT registration_status FROM import_resources WHERE file_path = ?",
        ("test/file5.txt",),
    )
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == RegistrationStatus.failed_unknown_error.value


def test_unique_constraint(db: ImportResourcesDB) -> None:
    """Test that unique constraint prevents duplicate file paths."""
    entry1 = create_test_entry("test/file6.txt")
    entry2 = create_test_entry("test/file6.txt")  # Same file path

    # Insert the first entry
    db.insert_pending(entry1)

    # Try to insert the second entry with the same file path
    # This should raise an sqlite3.IntegrityError
    with pytest.raises(Exception):  # sqlite3.IntegrityError
        db.insert_pending(entry2)


def test_close_connection(db: ImportResourcesDB) -> None:
    """Test that database connection is properly closed."""
    # Insert an entry to make sure the connection is working
    entry = create_test_entry("test/file7.txt")
    db.insert_pending(entry)

    # Close the connection
    db.close()

    # Try to use the connection after closing (should fail)
    with pytest.raises(Exception):
        db.conn.cursor()


def test_multiple_entries(db: ImportResourcesDB) -> None:
    """Test inserting and managing multiple entries."""
    entries = [
        create_test_entry("test/multi1.txt", 1024, 1000000000, "checksum1"),
        create_test_entry("test/multi2.txt", 2048, 1000000001, "checksum2"),
        create_test_entry("test/multi3.txt", 4096, 1000000002, "checksum3"),
    ]

    # Insert all entries
    entry_ids = []
    for entry in entries:
        entry_id = db.insert_pending(entry)
        entry_ids.append(entry_id)

    # Verify all entries were inserted
    assert len(entry_ids) == 3
    assert len(set(entry_ids)) == 3  # All IDs are unique

    # Update status of each entry
    for i, entry_id in enumerate(entry_ids):
        if i % 2 == 0:
            db.update_status(entry_id, RegistrationStatus.registered)
        else:
            db.update_status(entry_id, RegistrationStatus.failed_unknown_error)

    # Verify the status updates
    cursor = db.conn.cursor()
    cursor.execute("SELECT registration_status FROM import_resources ORDER BY id")
    results = cursor.fetchall()

    assert results[0][0] == RegistrationStatus.registered.value
    assert results[1][0] == RegistrationStatus.failed_unknown_error.value
    assert results[2][0] == RegistrationStatus.registered.value


def test_empty_entries_list(db: ImportResourcesDB) -> None:
    """Test handling of empty entries list in get_unregistered."""
    entries = []
    unregistered = db.get_unregistered(entries)

    assert unregistered == []


def test_status_updated_at_updates(db: ImportResourcesDB, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that status_updated_at timestamp is updated on status changes."""
    # Mock time.time() to return predictable, increasing values
    time_values = iter([1000000000, 1000000001])
    monkeypatch.setattr(time, "time", lambda: next(time_values))

    entry = create_test_entry("test/file8.txt")
    entry_id = db.insert_pending(entry)

    # Get the initial timestamp
    cursor = db.conn.cursor()
    cursor.execute("SELECT status_updated_at FROM import_resources WHERE id = ?", (entry_id,))
    initial_timestamp = cursor.fetchone()[0]

    # Update the status (this will use the next time value)
    db.update_status(entry_id, RegistrationStatus.registered)

    # Get the updated timestamp
    cursor.execute("SELECT status_updated_at FROM import_resources WHERE id = ?", (entry_id,))
    updated_timestamp = cursor.fetchone()[0]

    # Verify the timestamp was updated
    assert updated_timestamp > initial_timestamp
    assert updated_timestamp == 1000000001


def test_registration_status_enum_values() -> None:
    """Test that RegistrationStatus enum has correct values."""
    assert RegistrationStatus.registered.value == 1
    assert RegistrationStatus.pending.value == 2
    assert RegistrationStatus.failed_unknown_error.value == 3
    assert RegistrationStatus.failed_deterministic.value == 4
    assert RegistrationStatus.failed_unknown_application.value == 5
