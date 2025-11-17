from pathlib import Path
from typing import Any

import pytest

from bfabric.entities.core.has_many import HasMany
from bfabric.entities.parameter import Parameter
from bfabric.entities.resource import Resource
from bfabric.entities.workunit import Workunit


@pytest.fixture()
def mock_data_dict() -> dict[str, Any]:
    return {
        "id": 30000,
        "classname": "workunit",
        "created": "2024-01-02 03:04:05",
        "application": {
            "classname": "application",
            "id": 1000,
            "name": "my app",
            "storage": {"classname": "storage", "id": 2000, "projectfolderprefix": "xyz"},
            "technology": ["Tech"],
        },
        "container": {"classname": "project", "id": 3000, "name": "test container"},
        "exportable": "true",
        "parameter": [
            {"classname": "parameter", "id": 8118},
            {"classname": "parameter", "id": 8122},
            {"classname": "parameter", "id": 8119},
        ],
        "status": "AVAILABLE",
    }


@pytest.fixture()
def mock_workunit(mock_data_dict: dict[str, Any], mock_client, bfabric_instance) -> Workunit:
    return Workunit(mock_data_dict, client=mock_client, bfabric_instance=bfabric_instance)


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
        [
            mocker.MagicMock(key="key1", value="value1", __getitem__=lambda _self, x: {"context": "APPLICATION"}[x]),
            mocker.MagicMock(key="key2", value="value2", __getitem__=lambda _self, x: {"context": "APPLICATION"}[x]),
            mocker.MagicMock(key="key3", value="value3", __getitem__=lambda _self, x: {"context": "SUBMITTER"}[x]),
        ],
    )
    assert mock_workunit.application_parameters == {"key1": "value1", "key2": "value2"}
    assert mock_workunit.submitter_parameters == {"key3": "value3"}


def test_container_when_project(mock_workunit) -> None:
    mock_workunit._data_dict["container"]["classname"] = "project"
    assert mock_workunit.container.classname == "project"
    assert mock_workunit.container.id == 3000


def test_container_when_order(mock_workunit) -> None:
    mock_workunit._data_dict["container"]["classname"] = "order"
    assert mock_workunit.container.classname == "order"
    assert mock_workunit.container.id == 3000


def test_store_output_folder(mock_workunit) -> None:
    assert (
        Path("xyz3000/bfabric/Tech/my_app/2024/2024-01/2024-01-02/workunit_30000") == mock_workunit.store_output_folder
    )


def test_repr() -> None:
    workunit = Workunit({"id": 30000}, client=None)
    assert repr(workunit) == "Workunit(data_dict={'id': 30000}, bfabric_instance=None)"


def test_str() -> None:
    workunit = Workunit({"id": 30000}, client=None)
    assert str(workunit) == repr(workunit)


if __name__ == "__main__":
    pytest.main()
