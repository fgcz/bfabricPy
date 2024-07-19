from typing import Any

import pytest

from bfabric.entities.workunit import Workunit


@pytest.fixture()
def mock_data_dict() -> dict[str, Any]:
    return {
        "id": 30000,
        "application": {"classname": "application", "id": 1000},
        "container": {"classname": "project", "id": 3000},
        "exportable": "true",
        "parameter": [
            {"classname": "parameter", "id": 8118},
            {"classname": "parameter", "id": 8122},
            {"classname": "parameter", "id": 8119},
        ],
        "status": "AVAILABLE",
    }


@pytest.fixture()
def mock_workunit(mock_data_dict: dict[str, Any]) -> Workunit:
    return Workunit(mock_data_dict)


def test_data_dict(mock_workunit: Workunit, mock_data_dict: dict[str, Any]) -> None:
    assert mock_workunit.data_dict == mock_data_dict
    assert mock_workunit.data_dict is not mock_data_dict


def test_parameter_id_list(mock_workunit: Workunit) -> None:
    assert mock_workunit.parameter_id_list == [8118, 8122, 8119]


def test_repr(mock_workunit: Workunit) -> None:
    assert repr(mock_workunit) == f"Workunit({repr(mock_workunit.data_dict)})"


def test_str(mock_workunit: Workunit) -> None:
    assert str(mock_workunit) == f"Workunit({repr(mock_workunit.data_dict)})"


if __name__ == "__main__":
    pytest.main()
