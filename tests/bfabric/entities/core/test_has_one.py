from typing import Any

import pytest

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne


@pytest.fixture
def data_dict() -> dict[str, Any]:
    return {"id": 1000, "classname": "mockentity"}


@pytest.fixture(params=[True, False])
def optional(request) -> bool:
    return request.param


@pytest.fixture
def entity(data_dict, bfabric_instance, optional):
    class MockEntity(Entity):
        field: HasOne = HasOne(bfabric_field="test_field", optional=optional)

    return MockEntity(data_dict=data_dict, bfabric_instance=bfabric_instance)


def test_get_when_exists(entity, mocker):
    mocker.patch.object(entity.refs, "get").side_effect = lambda key: {"test_field": "mock_entity"}[key]
    assert entity.field == "mock_entity"


def test_get_when_not_exists(entity, mocker, optional):
    mocker.patch.object(entity.refs, "get").side_effect = lambda key: {"test_field": None}[key]
    if not optional:
        with pytest.raises(ValueError) as err:
            _ = entity.field
        assert str(err.value) == "Field 'test_field' is required"
    else:
        assert entity.field is None
