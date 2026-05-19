from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_mock import MockerFixture

from bfabric.entities import ExternalJob, Workunit

if TYPE_CHECKING:
    from bfabric.typing import ApiResponseObjectType


@pytest.fixture()
def data_dict() -> ApiResponseObjectType:
    return {
        "id": 1,
        "cliententityclassname": "Workunit",
        "cliententityid": 5,
    }


def test_workunit_when_available(
    mocker: MockerFixture, mock_client, data_dict: ApiResponseObjectType, bfabric_instance
) -> None:
    workunit = mocker.Mock(name="workunit", spec=Workunit)
    mock_client.reader.read_id.return_value = workunit
    external_job = ExternalJob(data_dict, mock_client, bfabric_instance=bfabric_instance)
    assert external_job.workunit == workunit
    mock_client.reader.read_id.assert_called_once_with(
        entity_type="workunit", entity_id=5, bfabric_instance=bfabric_instance
    )


def test_workunit_when_wrong_class(
    mocker: MockerFixture, mock_client, data_dict: ApiResponseObjectType, bfabric_instance
) -> None:
    other_entity = mocker.Mock(name="other_entity")
    mock_client.reader.read_id.return_value = other_entity
    data_dict["cliententityclassname"] = "WrongClass"
    external_job = ExternalJob(data_dict, mock_client, bfabric_instance=bfabric_instance)
    assert external_job.workunit is None
