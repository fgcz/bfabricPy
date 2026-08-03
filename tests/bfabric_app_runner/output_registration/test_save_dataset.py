from pathlib import Path

import polars as pl
import pytest

from bfabric.entities import Dataset
from bfabric.operations.dataset.changes import DatasetChanges
from bfabric_app_runner.output_registration.register import _save_dataset
from bfabric_app_runner.specs.outputs_spec import SaveDatasetSpec, UpdateExisting


@pytest.fixture()
def mock_client(mocker):
    return mocker.MagicMock()


@pytest.fixture()
def mock_workunit_definition(mocker):
    mock = mocker.MagicMock()
    mock.registration.workunit_id = 42
    mock.registration.container_id = 7
    return mock


@pytest.fixture()
def csv_path(tmp_path) -> Path:
    path = tmp_path / "my_dataset.csv"
    path.write_text("a,b\n1,2\n3,4\n")
    return path


@pytest.fixture()
def parquet_path(tmp_path) -> Path:
    path = tmp_path / "my_dataset.parquet"
    pl.DataFrame({"a": [1, 3], "b": [2, 4]}).write_parquet(path)
    return path


@pytest.fixture()
def spec(csv_path) -> SaveDatasetSpec:
    return SaveDatasetSpec(local_path=csv_path, separator=",", name="my_dataset")


@pytest.fixture()
def mock_operations(mocker):
    """Patches the dataset operations imported into the register module."""
    return {
        "create": mocker.patch("bfabric_app_runner.output_registration.register.create_dataset"),
        "update": mocker.patch("bfabric_app_runner.output_registration.register.update_dataset"),
        "identify": mocker.patch("bfabric_app_runner.output_registration.register.identify_changes"),
    }


def _dataset(mocker, *, id_: int = 555):
    """Builds a Dataset-like mock carrying an ``.id``."""
    dataset = mocker.MagicMock()
    dataset.id = id_
    return dataset


def test_save_dataset_no_existing_creates(mock_client, mock_workunit_definition, spec, mock_operations):
    """When no dataset exists yet for the workunit, a new one is created."""
    mock_client.reader.query_one.return_value = None

    _save_dataset(spec, mock_client, mock_workunit_definition)

    mock_client.reader.query_one.assert_called_once_with(Dataset, {"workunitid": 42})
    mock_operations["create"].assert_called_once()
    _, table, params = mock_operations["create"].call_args.args
    assert params.name == "my_dataset"
    assert params.container_id == 7
    assert params.workunit_id == 42
    assert table.columns == ["a", "b"]
    mock_operations["update"].assert_not_called()


def test_save_dataset_reads_parquet(mock_client, mock_workunit_definition, parquet_path, mock_operations):
    """A parquet-format spec is read via pl.read_parquet and creates a new dataset."""
    spec = SaveDatasetSpec(local_path=parquet_path, format="parquet", name="my_dataset")
    mock_client.reader.query_one.return_value = None

    _save_dataset(spec, mock_client, mock_workunit_definition)

    mock_operations["create"].assert_called_once()
    _, table, params = mock_operations["create"].call_args.args
    assert params.name == "my_dataset"
    assert table.columns == ["a", "b"]
    assert table.to_dicts() == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    mock_operations["update"].assert_not_called()


def test_save_dataset_existing_unchanged_skips(mocker, mock_client, mock_workunit_definition, spec, mock_operations):
    """When an identical dataset already exists, nothing is written."""
    mock_client.reader.query_one.return_value = _dataset(mocker, id_=555)
    mock_operations["identify"].return_value = DatasetChanges()

    _save_dataset(spec, mock_client, mock_workunit_definition)

    mock_operations["identify"].assert_called_once()
    mock_operations["update"].assert_not_called()
    mock_operations["create"].assert_not_called()


def test_save_dataset_existing_changed_updates(mocker, mock_client, mock_workunit_definition, spec, mock_operations):
    """When the existing dataset differs, it is updated in place."""
    mock_client.reader.query_one.return_value = _dataset(mocker, id_=555)
    mock_operations["identify"].return_value = DatasetChanges(column_added=["c"])

    _save_dataset(spec, mock_client, mock_workunit_definition)

    mock_operations["update"].assert_called_once()
    args, kwargs = mock_operations["update"].call_args
    call = {**dict(zip(("client", "dataset_id", "table"), args)), **kwargs}
    assert call["dataset_id"] == 555
    assert call["table"].columns == ["a", "b"]
    mock_operations["create"].assert_not_called()


def test_save_dataset_existing_with_no_policy_raises(
    mocker, mock_client, mock_workunit_definition, csv_path, mock_operations
):
    """update_existing=NO refuses to overwrite an existing dataset."""
    spec = SaveDatasetSpec(local_path=csv_path, separator=",", name="my_dataset", update_existing=UpdateExisting.NO)
    mock_client.reader.query_one.return_value = _dataset(mocker, id_=555)

    with pytest.raises(ValueError, match="already exists"):
        _save_dataset(spec, mock_client, mock_workunit_definition)

    mock_operations["update"].assert_not_called()
    mock_operations["create"].assert_not_called()


def test_save_dataset_required_but_missing_raises(mock_client, mock_workunit_definition, csv_path, mock_operations):
    """update_existing=REQUIRED errors when no dataset exists to update."""
    spec = SaveDatasetSpec(
        local_path=csv_path, separator=",", name="my_dataset", update_existing=UpdateExisting.REQUIRED
    )
    mock_client.reader.query_one.return_value = None

    with pytest.raises(ValueError, match="does not exist"):
        _save_dataset(spec, mock_client, mock_workunit_definition)

    mock_operations["create"].assert_not_called()
    mock_operations["update"].assert_not_called()
