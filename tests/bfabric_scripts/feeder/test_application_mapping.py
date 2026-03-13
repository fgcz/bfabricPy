import datetime
from typing import Protocol

import polars as pl
import pytest
import pytest_mock
from pathlib import Path
from unittest.mock import MagicMock
import os

from bfabric_scripts.feeder.application_mapping import (
    SystemConfig,
    load_or_update_cache,
)


@pytest.fixture
def mock_client_result(mocker: pytest_mock.MockerFixture) -> MagicMock:
    """Fixture to create a mock result from client.read()."""
    # Mock the result.to_polars() call
    mock_result = mocker.MagicMock()

    # Create test data matching what client.read() would return
    # It should have columns: id, name, technology, created, modified
    test_data = pl.DataFrame(
        {
            "id": [1, 2],
            "name": ["App1", "App2"],
            "technology": [[2, 4], [2, 4]],
            "created": [datetime.datetime(2024, 1, 1), datetime.datetime(2024, 1, 2)],
            "modified": [datetime.datetime(2024, 1, 10), datetime.datetime(2024, 1, 11)],
        }
    )

    mock_result.to_polars.return_value = test_data
    return mock_result


@pytest.fixture
def mock_client(mocker: pytest_mock.MockerFixture, mock_client_result: MagicMock) -> MagicMock:
    """Fixture to create a mock Bfabric client."""
    client = mocker.MagicMock()
    client.read.return_value = mock_client_result
    client.config.base_url = "https://bfabric.example.org/bfabric/"
    return client


@pytest.fixture
def cache_file_path(tmp_path: Path) -> Path:
    """Fixture to provide a cache file path in the tmp_path directory."""
    return tmp_path / "application_mapping_cache.tsv"


class CacheLoader(Protocol):
    """Protocol for the cache loader callable."""

    def __call__(self, ttl_hours: float = 24.0) -> pl.DataFrame:
        """Load the cache with the given TTL."""
        ...


@pytest.fixture
def cache_loader(
    mock_client: MagicMock,
    cache_file_path: Path,
) -> CacheLoader:
    """Fixture to provide a callable that loads cache with given TTL."""

    def load(ttl_hours: float = 24.0) -> pl.DataFrame:
        return load_or_update_cache(
            path=cache_file_path,
            client=mock_client,
            config=SystemConfig(),
            ttl_hours=ttl_hours,
        )

    return load


def create_cached_data(cache_file_path: Path, hours_old: int = 0) -> None:
    """Helper function to create a cached file with a specific age."""
    test_data = pl.DataFrame(
        {
            "application_id": [100],
            "application_uri": ["bfabric://cached.org/application/100"],
            "application_name": ["CachedApp"],
            "technology": [2],
            "created": ["2024-01-01T00:00:00"],
            "modified": ["2024-01-10T00:00:00"],
        }
    )

    cache_file_path.write_bytes(test_data.write_csv(separator="\t").encode())

    # Set the file's modification time
    if hours_old > 0:
        old_time = datetime.datetime.now() - datetime.timedelta(hours=hours_old)
        timestamp = old_time.timestamp()

        _ = os.utime(cache_file_path, (timestamp, timestamp))


def test_load_or_update_cache_cache_not_exists(
    cache_file_path: Path,
    cache_loader: CacheLoader,
    mock_client: MagicMock,
) -> None:
    """Test that cache is populated when it doesn't exist."""
    scenario = "cache_not_exists"
    assert not cache_file_path.exists(), f"Test setup error: cache file should not exist for scenario '{scenario}'"

    result = cache_loader(ttl_hours=24.0)

    # Verify client.read was called
    mock_client.read.assert_called_once()

    # Verify the result has the expected structure
    assert isinstance(result, pl.DataFrame)
    assert "application_id" in result.columns
    assert "application_uri" in result.columns
    assert "application_name" in result.columns
    assert "technology" in result.columns

    # Verify cache file was created
    assert cache_file_path.exists()

    # Verify the cache file can be read
    cached_data = pl.read_csv(cache_file_path, separator="\t")
    assert len(cached_data) == 4  # 2 applications * 2 technologies


def test_load_or_update_cache_cache_valid(
    cache_file_path: Path,
    cache_loader: CacheLoader,
    mock_client: MagicMock,
) -> None:
    """Test that cache is used when it exists and is valid."""

    # Create a recent cache file (1 hour old)
    create_cached_data(cache_file_path, hours_old=1)

    result = cache_loader(ttl_hours=24.0)

    # Verify client.read was NOT called (cache was used)
    mock_client.read.assert_not_called()

    # Verify the result is the cached data
    assert isinstance(result, pl.DataFrame)
    assert len(result) == 1
    assert result["application_name"][0] == "CachedApp"


def test_load_or_update_cache_cache_expired(
    cache_file_path: Path,
    cache_loader: CacheLoader,
    mock_client: MagicMock,
) -> None:
    """Test that cache is repopulated when it exists but is expired."""

    # Create an expired cache file (25 hours old)
    create_cached_data(cache_file_path, hours_old=25)

    result = cache_loader(ttl_hours=24.0)

    # Verify client.read was called (cache was expired)
    mock_client.read.assert_called_once()

    # Verify the result has the expected structure (not the cached data)
    assert isinstance(result, pl.DataFrame)
    assert "App1" in result["application_name"].to_list() or "App2" in result["application_name"].to_list()
    assert len(result) == 4  # 2 applications * 2 technologies


def test_load_or_update_cache_custom_ttl(
    cache_file_path: Path,
    cache_loader: CacheLoader,
    mock_client: MagicMock,
) -> None:
    """Test that custom TTL is respected."""
    # Create a cache file that is 3 hours old
    create_cached_data(cache_file_path, hours_old=3)

    # With TTL of 2 hours, the cache should be expired
    result = cache_loader(ttl_hours=2.0)

    # Verify client.read was called (cache was expired relative to custom TTL)
    mock_client.read.assert_called_once()

    # Verify the result is from the client, not the cache
    assert isinstance(result, pl.DataFrame)
    assert len(result) == 4  # 2 applications * 2 technologies


def test_load_or_update_cache_filtering(
    mocker: pytest_mock.MockerFixture,
    mock_client: MagicMock,
    cache_file_path: Path,
) -> None:
    """Test that applications are filtered by the name regex."""
    # Mock data with various application names
    mock_result = mocker.MagicMock()
    test_data = pl.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "name": ["ValidApp", "Invalid-App", "AnotherValid", "Invalid App"],
            "technology": [[2], [2], [4], [4]],
            "created": [datetime.datetime(2024, 1, 1)] * 4,
            "modified": [datetime.datetime(2024, 1, 10)] * 4,
        }
    )
    mock_result.to_polars.return_value = test_data
    mock_client.read.return_value = mock_result

    result = load_or_update_cache(
        path=cache_file_path,
        client=mock_client,
        config=SystemConfig(),
        ttl_hours=24.0,
    )

    # Verify that only valid names (matching regex ^[a-zA-Z0-9_]+$) are included
    assert len(result) == 2  # Only ValidApp and AnotherValid
    assert "ValidApp" in result["application_name"].to_list()
    assert "AnotherValid" in result["application_name"].to_list()
    assert "Invalid-App" not in result["application_name"].to_list()
    assert "Invalid App" not in result["application_name"].to_list()
