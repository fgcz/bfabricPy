import pytest
from bfabric_app_runner.inputs.resolve._resolve_bfabric_dataset_specs import ResolveBfabricDatasetSpecs

from bfabric.entities import Dataset
from bfabric.entities.core.entity_reader import EntityResult
from bfabric.entities.core.uri import EntityUri


def _dataset_uri(dataset_id: int) -> EntityUri:
    return EntityUri(f"https://fgcz-bfabric.uzh.ch/bfabric/dataset/show.html?id={dataset_id}")


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture
def resolver(mock_client):
    return ResolveBfabricDatasetSpecs(mock_client.reader)


def test_call(resolver, mocker, mock_client):
    # Setup test data
    mock_dataset = mocker.MagicMock(name="mock_dataset")
    mock_dataset.get_csv.return_value = "csv content"

    # Mock reader.read_ids to return our mock dataset keyed by URI
    mock_client.reader.read_ids.return_value = EntityResult({_dataset_uri(1): mock_dataset})

    # Create mock specs
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.id = 1
    mock_spec.format = "csv"
    mock_spec.separator = ","
    mock_spec.filename = "test.csv"

    specs = [mock_spec]

    # Call the function under test
    result = resolver(specs)

    # Assert the results
    assert len(result) == 1
    assert result[0].filename == "test.csv"
    assert result[0].content == "csv content"

    # Verify the correct methods were called
    mock_client.reader.read_ids.assert_called_once_with(Dataset, [1])
    mock_dataset.get_csv.assert_called_once_with(separator=",")


def test_call_when_dataset_missing_raises_key_error(resolver, mocker, mock_client):
    """A not-found dataset is None in read_ids' result and is filtered out on re-key, so indexing it
    by id raises KeyError downstream (matching the previous find_all behavior of dropping misses)."""
    found = mocker.MagicMock(name="found_dataset")
    found.get_csv.return_value = "csv content"
    # id=1 found, id=2 missing (None)
    mock_client.reader.read_ids.return_value = EntityResult({_dataset_uri(1): found, _dataset_uri(2): None})

    spec_found = mocker.MagicMock(name="spec_found")
    spec_found.id = 1
    spec_found.format = "csv"
    spec_found.separator = ","
    spec_found.filename = "found.csv"
    spec_missing = mocker.MagicMock(name="spec_missing")
    spec_missing.id = 2
    spec_missing.format = "csv"
    spec_missing.separator = ","
    spec_missing.filename = "missing.csv"

    with pytest.raises(KeyError):
        resolver([spec_found, spec_missing])


def test_call_when_empty(resolver):
    specs = []
    result = resolver(specs)
    assert result == []


def test_get_content_when_csv(mocker, resolver, mock_client):
    dataset = mocker.MagicMock(name="dataset")
    spec = mocker.MagicMock(name="spec")
    spec.format = "csv"
    spec.separator = ","
    mock_client.Dataset.find_all.return_value = {1: dataset}
    dataset.get_csv.return_value = "csv content"

    result = resolver._get_content(dataset, spec)

    assert result == "csv content"
    dataset.get_csv.assert_called_once_with(separator=",")


def test_get_content_when_parquet(mocker, resolver, mock_client):
    dataset = mocker.MagicMock(name="dataset")
    spec = mocker.MagicMock(name="spec")
    spec.format = "parquet"
    mock_client.Dataset.find_all.return_value = {1: dataset}
    dataset.get_parquet.return_value = "parquet content"

    result = resolver._get_content(dataset, spec)

    assert result == "parquet content"
    dataset.get_parquet.assert_called_once_with()
