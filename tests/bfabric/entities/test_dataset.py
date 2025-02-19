from __future__ import annotations

from typing import Any

import polars as pl
import polars.testing
import pytest
from pytest_mock import MockFixture, MockerFixture

from bfabric.entities.dataset import Dataset


@pytest.fixture()
def mock_data_dict() -> dict[str, Any]:
    return {
        "id": 1234,
        "attribute": [
            {"name": "Color", "position": "1"},
            {"name": "Shape", "position": "2"},
        ],
        "item": [
            {"field": [{"value": "Red", "attributeposition": "1"}, {"value": "Square", "attributeposition": "2"}]},
            {"field": [{"value": "Blue", "attributeposition": "1"}, {"value": "Circle", "attributeposition": "2"}]},
        ],
    }


@pytest.fixture()
def mock_data_dict_rearranged() -> dict[str, Any]:
    return {
        "id": 1234,
        "attribute": [
            {"name": "Color", "position": "1"},
            {"name": "Shape", "position": "2"},
        ],
        "item": [
            {"field": [{"value": "Square", "attributeposition": "2"}, {"value": "Red", "attributeposition": "1"}]},
            {"field": [{"value": "Circle", "attributeposition": "2"}, {"value": "Blue", "attributeposition": "1"}]},
        ],
    }


@pytest.fixture()
def mock_client(mocker: MockerFixture):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture()
def mock_dataset(mock_data_dict: dict[str, Any], mock_client) -> Dataset:
    return Dataset(mock_data_dict, client=mock_client)


@pytest.fixture()
def mock_empty_dataset() -> Dataset:
    return Dataset({"id": 1234, "attribute": [], "item": []}, client=None)


def test_data_dict(mock_dataset: Dataset, mock_data_dict: dict[str, Any]) -> None:
    assert mock_dataset.data_dict == mock_data_dict
    assert mock_dataset.data_dict is not mock_data_dict


@pytest.mark.parametrize("rearranged_data_dict", [True, False])
def test_to_polars(request, rearranged_data_dict: bool) -> None:
    data_dict = request.getfixturevalue("mock_data_dict_rearranged" if rearranged_data_dict else "mock_data_dict")
    mock_dataset = Dataset(data_dict, client=None)
    df = mock_dataset.to_polars()
    pl.testing.assert_frame_equal(
        df,
        pl.DataFrame(
            {
                "Color": ["Red", "Blue"],
                "Shape": ["Square", "Circle"],
            }
        ),
    )


def test_write_csv(mocker: MockFixture, mock_dataset: Dataset) -> None:
    mock_to_polars = mocker.patch.object(mock_dataset, "to_polars")
    mock_df = mocker.MagicMock(name="mock_df")
    mock_to_polars.return_value = mock_df
    mock_path = mocker.MagicMock(name="mock_path")
    mock_sep = mocker.MagicMock(name="mock_sep")

    mock_dataset.write_csv(mock_path, separator=mock_sep)

    mock_df.write_csv.assert_called_once_with(mock_path, separator=mock_sep)


def test_repr(mock_empty_dataset: Dataset) -> None:
    assert repr(mock_empty_dataset) == "Dataset({'id': 1234, 'attribute': [], 'item': []}, client=None)"


def test_str(mock_empty_dataset: Dataset) -> None:
    assert str(mock_empty_dataset) == "Dataset({'id': 1234, 'attribute': [], 'item': []}, client=None)"


if __name__ == "__main__":
    pytest.main()
