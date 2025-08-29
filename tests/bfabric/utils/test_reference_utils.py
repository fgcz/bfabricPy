"""Tests for reference_utils module."""

import pytest

from bfabric.utils.reference_utils import read_reference


@pytest.fixture
def mock_bfabric_client(mocker):
    """Create a mock Bfabric client."""
    client = mocker.MagicMock()
    return client


def test_read_reference_when_result_found(mock_bfabric_client):
    """Test read_reference when exactly one result is found."""
    mock_result = [{"id": 123, "name": "test_entity"}]
    mock_bfabric_client.read.return_value = mock_result

    reference = {"classname": "sample", "id": 123}
    result = read_reference(mock_bfabric_client, reference)

    assert result == {"id": 123, "name": "test_entity"}
    mock_bfabric_client.read.assert_called_once_with("sample", {"id": 123}, max_results=1, check=True)


def test_read_reference_when_no_result_found(mock_bfabric_client):
    """Test read_reference when no result is found."""
    mock_bfabric_client.read.return_value = []

    reference = {"classname": "sample", "id": 999}
    result = read_reference(mock_bfabric_client, reference)

    assert result is None
    mock_bfabric_client.read.assert_called_once_with("sample", {"id": 999}, max_results=1, check=True)


def test_read_reference_when_multiple_results_found(mock_bfabric_client):
    """Test read_reference when multiple results are found (should not happen but handled gracefully)."""
    mock_result = [{"id": 123, "name": "test_entity1"}, {"id": 124, "name": "test_entity2"}]
    mock_bfabric_client.read.return_value = mock_result

    reference = {"classname": "sample", "id": 123}
    result = read_reference(mock_bfabric_client, reference)

    assert result is None
    mock_bfabric_client.read.assert_called_once_with("sample", {"id": 123}, max_results=1, check=True)


def test_read_reference_with_check_false(mock_bfabric_client):
    """Test read_reference with check=False parameter."""
    mock_result = [{"id": 123, "name": "test_entity"}]
    mock_bfabric_client.read.return_value = mock_result

    reference = {"classname": "workunit", "id": 456}
    result = read_reference(mock_bfabric_client, reference, check=False)

    assert result == {"id": 123, "name": "test_entity"}
    mock_bfabric_client.read.assert_called_once_with("workunit", {"id": 456}, max_results=1, check=False)