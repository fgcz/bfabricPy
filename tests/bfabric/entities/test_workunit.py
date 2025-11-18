from pathlib import Path
from typing import Any

import pytest

from bfabric.entities.workunit import Workunit


@pytest.fixture()
def data_dict() -> dict[str, Any]:
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
            {"classname": "parameter", "id": 8118, "key": "param8118", "value": "test1", "context": "APPLICATION"},
            {"classname": "parameter", "id": 8122, "key": "param8122", "value": "test2", "context": "APPLICATION"},
            {"classname": "parameter", "id": 8119, "key": "param8119", "value": "test3", "context": "SUBMITTER"},
        ],
        "status": "AVAILABLE",
        "resource": [
            {"classname": "resource", "id": 1000, "name": "my resource"},
        ],
        "inputresource": [
            {"classname": "resource", "id": 500, "name": "input resource"},
        ],
    }


@pytest.fixture()
def workunit(data_dict, mock_client, bfabric_instance) -> Workunit:
    return Workunit(data_dict, client=mock_client, bfabric_instance=bfabric_instance)


def test_data_dict(workunit: Workunit, data_dict) -> None:
    assert workunit.data_dict == data_dict
    assert workunit.data_dict is not data_dict


def test_parameters(workunit) -> None:
    # TODO drop sorting?
    assert workunit.parameters.ids == [8118, 8122, 8119]


def test_application_parameters(workunit) -> None:
    assert workunit.application_parameters == {
        "param8118": "test1",
        "param8122": "test2",
    }


def test_submitter_parameters(workunit) -> None:
    assert workunit.submitter_parameters == {
        "param8119": "test3",
    }


def test_resources(workunit) -> None:
    assert workunit.resources.ids == [1000]


def test_input_resources(workunit) -> None:
    assert workunit.input_resources.ids == [500]


def test_parameter_values(mocker, workunit: Workunit) -> None:
    mocker.patch.object(
        workunit,
        "parameters",
        [
            mocker.MagicMock(key="key1", value="value1", __getitem__=lambda _self, x: {"context": "APPLICATION"}[x]),
            mocker.MagicMock(key="key2", value="value2", __getitem__=lambda _self, x: {"context": "APPLICATION"}[x]),
            mocker.MagicMock(key="key3", value="value3", __getitem__=lambda _self, x: {"context": "SUBMITTER"}[x]),
        ],
    )
    assert workunit.application_parameters == {"key1": "value1", "key2": "value2"}
    assert workunit.submitter_parameters == {"key3": "value3"}


def test_container_when_project(workunit) -> None:
    workunit._Entity__data_dict["container"]["classname"] = "project"
    assert workunit.container.classname == "project"
    assert workunit.container.id == 3000


def test_container_when_order(workunit) -> None:
    workunit._Entity__data_dict["container"]["classname"] = "order"
    assert workunit.container.classname == "order"
    assert workunit.container.id == 3000


def test_store_output_folder(workunit) -> None:
    assert Path("xyz3000/bfabric/Tech/my_app/2024/2024-01/2024-01-02/workunit_30000") == workunit.store_output_folder


def test_repr() -> None:
    workunit = Workunit({"id": 30000}, client=None)
    assert repr(workunit) == "Workunit(data_dict={'id': 30000}, bfabric_instance=None)"


def test_str() -> None:
    workunit = Workunit({"id": 30000}, client=None)
    assert str(workunit) == repr(workunit)


if __name__ == "__main__":
    pytest.main()
