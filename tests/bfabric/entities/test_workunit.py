from pathlib import Path
from typing import Any

import pytest
from pytest_mock import MockerFixture

from bfabric.entities import Project, Order
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.parameter import Parameter
from bfabric.entities.resource import Resource
from bfabric.entities.workunit import Workunit


@pytest.fixture()
def mock_data_dict() -> dict[str, Any]:
    return {
        "id": 30000,
        "created": "2024-01-02 03:04:05",
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


def test_parameters(mocker, mock_workunit) -> None:
    get = mocker.patch.object(HasMany, "__get__")
    assert mock_workunit.parameters == get.return_value
    assert get.call_args[0][0]._entity_type == Parameter
    assert get.call_args[0][0]._bfabric_field == "parameter"
    assert get.call_args[0][0]._ids_property is None


def test_resources(mocker, mock_workunit) -> None:
    get = mocker.patch.object(HasMany, "__get__")
    assert mock_workunit.resources == get.return_value
    assert get.call_args[0][0]._entity_type == Resource
    assert get.call_args[0][0]._bfabric_field == "resource"
    assert get.call_args[0][0]._ids_property is None


def test_input_resources(mocker, mock_workunit) -> None:
    get = mocker.patch.object(HasMany, "__get__")
    assert mock_workunit.input_resources == get.return_value
    assert get.call_args[0][0]._entity_type == Resource
    assert get.call_args[0][0]._bfabric_field == "inputresource"
    assert get.call_args[0][0]._ids_property is None


def test_parameter_values(mocker, mock_workunit: Workunit) -> None:
    mocker.patch.object(
        mock_workunit,
        "parameters",
        mocker.Mock(
            list=[
                mocker.Mock(key="key1", value="value1"),
                mocker.Mock(key="key2", value="value2"),
            ]
        ),
    )
    assert mock_workunit.parameter_values == {"key1": "value1", "key2": "value2"}


def test_container_when_project(mocker, mock_workunit) -> None:
    mock_find = mocker.patch.object(Project, "find")
    assert mock_workunit.container == mock_find.return_value
    mock_find.assert_called_once_with(id=3000, client=mock_workunit._client)


def test_container_when_order(mocker, mock_workunit, mock_data_dict) -> None:
    mock_find = mocker.patch.object(Order, "find")
    mock_data_dict["container"]["classname"] = "order"
    assert mock_workunit.container == mock_find.return_value
    mock_find.assert_called_once_with(id=3000, client=mock_workunit._client)


def test_store_output_folder(mocker, mock_workunit) -> None:
    mock_application = mocker.MagicMock(storage={"projectfolderprefix": "xyz"})
    mock_application.__getitem__.side_effect = {
        "technology": "tech",
        "name": "my app",
    }.__getitem__
    mocker.patch.object(mock_workunit, "application", mock_application)
    mocker.patch.object(Workunit, "container", mocker.PropertyMock(return_value=mocker.MagicMock(id=12)))
    assert Path("xyz12/bfabric/tech/my_app/2024/2024-01/2024-01-02/workunit_30000") == mock_workunit.store_output_folder


def test_repr() -> None:
    workunit = Workunit({"id": 30000}, client=None)
    assert repr(workunit) == "Workunit({'id': 30000}, client=None)"


def test_str() -> None:
    workunit = Workunit({"id": 30000}, client=None)
    assert repr(workunit) == "Workunit({'id': 30000}, client=None)"


if __name__ == "__main__":
    pytest.main()
