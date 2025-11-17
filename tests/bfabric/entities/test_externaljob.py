from typing import Any

import pytest
from pytest_mock import MockerFixture

from bfabric.entities import ExternalJob, Workunit


@pytest.fixture()
def data_dict():
    return {
        "id": 1,
        "cliententityclassname": "Workunit",
        "cliententityid": 5,
    }


def test_workunit_when_available(mocker: MockerFixture, data_dict: dict[str, Any], bfabric_instance):
    mock_client = mocker.MagicMock(name="mock_client", spec=[])
    mock_find = mocker.patch.object(Workunit, "find")
    external_job = ExternalJob(data_dict, mock_client, bfabric_instance=bfabric_instance)
    assert external_job.workunit == mock_find.return_value
    mock_find.assert_called_once_with(id=5, client=mock_client)


def test_workunit_when_wrong_class(mocker: MockerFixture, data_dict: dict[str, Any], bfabric_instance):
    mock_client = mocker.MagicMock(name="mock_client", spec=[])
    mock_find = mocker.patch.object(Workunit, "find")
    # TODO actually check which ones are the legal values here
    data_dict["cliententityclassname"] = "WrongClass"
    external_job = ExternalJob(data_dict, mock_client, bfabric_instance=bfabric_instance)
    assert external_job.workunit is None
    mock_find.assert_not_called()
