from __future__ import annotations

from typing import Any

import pytest
from pytest_mock import MockFixture

from bfabric.entities.dataset import Dataset


@pytest.fixture()
def mock_data_dict() -> dict[str, Any]:
    return {
        "id": 1234,
        "attribute": [
            {"name": "Color"},
            {"name": "Shape"},
        ],
        "item": [
            {"field": [{"value": "Red"}, {"value": "Square"}]},
            {"field": [{"value": "Blue"}, {"value": "Circle"}]},
        ],
    }


@pytest.fixture()
def mock_dataset(mock_data_dict: dict[str, Any]) -> Dataset:
    return Dataset(mock_data_dict)


@pytest.fixture()
def mock_empty_dataset() -> Dataset:
    return Dataset({"id": 1234, "attribute": [], "item": []})


def test_dict(mock_dataset: Dataset, mock_data_dict: dict[str, Any]) -> None:
    assert mock_dataset.dict == mock_data_dict
    assert mock_dataset.dict is not mock_data_dict


def test_to_polars(mock_dataset: Dataset) -> None:
    df = mock_dataset.to_polars()
    assert df.columns.to_list() == ["Color", "Shape"]
    assert df.shape == (2, 2)
    assert df["Color"].to_list() == ["Red", "Blue"]
    assert df["Shape"].to_list() == ["Square", "Circle"]


def test_write_csv(mocker: MockFixture, mock_dataset: Dataset) -> None:
    mock_to_polars = mocker.patch.object(mock_dataset, "to_polars")
    mock_df = mocker.MagicMock(name="mock_df")
    mock_to_polars.return_value = mock_df
    mock_path = mocker.MagicMock(name="mock_path")
    mock_sep = mocker.MagicMock(name="mock_sep")

    mock_dataset.write_csv(mock_path, sep=mock_sep)

    mock_df.to_csv.assert_called_once_with(mock_path, sep=mock_sep, index=False)


def test_repr(mock_empty_dataset: Dataset) -> None:
    assert repr(mock_empty_dataset) == "Dataset({'id': 1234, 'attribute': [], 'item': []})"


def test_str(mock_empty_dataset: Dataset) -> None:
    assert str(mock_empty_dataset) == "Dataset({'id': 1234, 'attribute': [], 'item': []})"


if __name__ == "__main__":
    pytest.main()
