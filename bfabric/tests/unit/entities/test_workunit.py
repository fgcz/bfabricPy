from typing import Any

import pytest
from pytest_mock import MockerFixture

from bfabric.entities.parameter import Parameter
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
def mock_client(mocker: MockerFixture):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture()
def mock_workunit(mock_data_dict: dict[str, Any], mock_client) -> Workunit:
    return Workunit(mock_data_dict, client=mock_client)


def test_data_dict(mock_workunit: Workunit, mock_data_dict: dict[str, Any]) -> None:
    assert mock_workunit.data_dict == mock_data_dict
    assert mock_workunit.data_dict is not mock_data_dict


def test_parameter_id_list(mock_workunit: Workunit) -> None:
    assert mock_workunit._parameter_id_list == [8118, 8122, 8119]


def test_parameters(mocker, mock_workunit, mock_client) -> None:
    mock_find_all = mocker.patch.object(Parameter, "find_all")
    assert mock_workunit.parameters == mock_find_all.return_value
    mock_find_all.assert_called_once_with(ids=[8118, 8122, 8119], client=mock_client)


def test_parameter_values(mocker, mock_workunit: Workunit) -> None:
    mocker.patch.object(
        mock_workunit,
        "parameters",
        {1234: mocker.Mock(key="key1", value="value1"), 5678: mocker.Mock(key="key2", value="value2")},
    )
    assert mock_workunit.parameter_values == {"key1": "value1", "key2": "value2"}


def test_repr() -> None:
    workunit = Workunit({"id": 30000}, client=None)
    assert repr(workunit) == "Workunit({'id': 30000}, client=None)"


def test_str() -> None:
    workunit = Workunit({"id": 30000}, client=None)
    assert repr(workunit) == "Workunit({'id': 30000}, client=None)"


if __name__ == "__main__":
    pytest.main()
