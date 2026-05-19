from __future__ import annotations

import polars as pl
import pytest

from bfabric.entities import Dataset
from bfabric.operations.dataset import (
    CreateDatasetParams,
    create_dataset,
    preview_dataset_update,
    update_dataset,
)


@pytest.fixture
def mock_client(mocker):
    client = mocker.MagicMock(name="Bfabric")
    client.config.base_url = "https://test.example.com/bfabric/"
    return client


def _table() -> pl.DataFrame:
    return pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})


def test_create_dataset_payload_shape(mock_client):
    mock_client.save.return_value = [{"id": 11, "classname": "dataset", "_entityclass": "dataset"}]
    dataset = create_dataset(
        mock_client,
        _table(),
        CreateDatasetParams(name="ds1", container_id=100, workunit_id=200),
    )

    assert dataset.id == 11
    endpoint, obj = mock_client.save.call_args.args
    assert endpoint == "dataset"
    assert obj["name"] == "ds1"
    assert obj["containerid"] == 100
    assert obj["workunitid"] == 200
    assert "attribute" in obj and "item" in obj


def test_create_dataset_returned_entity_has_usable_uri(mock_client):
    """Returned dataset must expose a working `.uri` (regression smoke for SOAP response shape)."""
    mock_client.save.return_value = [{"id": 11, "classname": "dataset", "_entityclass": "dataset"}]
    dataset = create_dataset(
        mock_client,
        _table(),
        CreateDatasetParams(name="ds1", container_id=100),
    )
    assert str(dataset.uri) == "https://test.example.com/bfabric/dataset/show.html?id=11"


def test_create_dataset_without_workunit(mock_client):
    mock_client.save.return_value = [{"id": 12, "classname": "dataset", "_entityclass": "dataset"}]
    create_dataset(mock_client, _table(), CreateDatasetParams(name="ds", container_id=1))
    _, obj = mock_client.save.call_args.args
    assert "workunitid" not in obj


def test_update_dataset_payload_shape(mock_client):
    mock_client.save.return_value = [{"id": 11, "classname": "dataset", "_entityclass": "dataset"}]
    updated = update_dataset(mock_client, dataset_id=11, table=_table())

    assert updated.id == 11
    endpoint, obj = mock_client.save.call_args.args
    assert endpoint == "dataset"
    assert obj["id"] == 11
    assert "attribute" in obj and "item" in obj


def test_preview_dataset_update_reports_changes(mock_client, mocker):
    existing = mocker.MagicMock(spec=Dataset)
    existing.to_polars.return_value = pl.DataFrame({"a": [1, 2]})
    mock_client.reader.read_id.return_value = existing

    new_table = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    preview = preview_dataset_update(mock_client, dataset_id=42, new_table=new_table)

    assert preview.current is existing
    assert preview.changes.column_added == ["b"]


def test_preview_dataset_update_raises_on_missing(mock_client):
    mock_client.reader.read_id.return_value = None
    with pytest.raises(RuntimeError, match="Dataset 99 not found"):
        preview_dataset_update(mock_client, dataset_id=99, new_table=_table())
