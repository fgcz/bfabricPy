import pytest
from bfabric_app_runner.inputs.resolve._resolve_bfabric_dataset_specs import ResolveBfabricDatasetSpecs

from bfabric.entities import Dataset


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture
def resolver(mock_client):
    return ResolveBfabricDatasetSpecs(mock_client)


def test_call(resolver, mocker, mock_client):
    # Setup test data
    mock_dataset = mocker.MagicMock(name="mock_dataset")
    mock_dataset.get_csv.return_value = "csv content"

    # Mock Dataset.find_all to return our mock dataset
    mocker.patch.object(Dataset, "find_all", return_value={1: mock_dataset})

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
    Dataset.find_all.assert_called_once_with(ids=[1], client=mock_client)
    mock_dataset.get_csv.assert_called_once_with(separator=",")


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
