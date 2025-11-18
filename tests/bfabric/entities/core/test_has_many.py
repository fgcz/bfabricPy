import polars as pl
import polars.testing
import pytest

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany


@pytest.fixture
def optional(request) -> bool:
    if hasattr(request, "param"):
        return request.param
    return False


@pytest.fixture
def data_dict():
    return {
        "classname": "mock",
        "id": 1000,
        "many": [
            {"id": 10, "classname": "testreferenced", "name": "Referenced Entity 10"},
            {"id": 20, "classname": "testreferenced", "name": "Referenced Entity 20"},
        ],
    }


@pytest.fixture
def entity(bfabric_instance, optional, data_dict):
    class MockEntity(Entity):
        field: HasMany = HasMany(bfabric_field="many", optional=optional)

    return MockEntity(data_dict=data_dict, bfabric_instance=bfabric_instance)


class TestFunctionality:
    @staticmethod
    def test_ids(entity):
        assert entity.field.ids == [10, 20]

    @staticmethod
    def test_list(entity):
        result = entity.field.list
        assert len(result) == 2
        assert result[0].id == 10
        assert result[0].classname == "testreferenced"
        assert result[0]["name"] == "Referenced Entity 10"
        assert result[1].id == 20
        assert result[1].classname == "testreferenced"
        assert result[1]["name"] == "Referenced Entity 20"

    @staticmethod
    def test_polars(entity):
        result = entity.field.polars
        expected = pl.from_dicts(
            [
                {"id": 10, "classname": "testreferenced", "name": "Referenced Entity 10"},
                {"id": 20, "classname": "testreferenced", "name": "Referenced Entity 20"},
            ]
        )
        pl.testing.assert_frame_equal(expected, result)

    @staticmethod
    def test_len(entity):
        assert len(entity.field) == 2

    @staticmethod
    def test_iter(entity):
        collect = list(entity.field)
        assert len(collect) == 2
        assert collect[0].id == 10
        assert collect[1].id == 20

    @staticmethod
    def test_repr(entity):
        assert (
            repr(entity)
            == "MockEntity(data_dict={'classname': 'mock', 'id': 1000, 'many': [{'id': 10, 'classname': 'testreferenced', 'name': 'Referenced Entity 10'}, {'id': 20, 'classname': 'testreferenced', 'name': 'Referenced Entity 20'}]}, bfabric_instance='https://bfabric.example.org/bfabric/')"
        )

    @staticmethod
    def test_str(entity):
        assert str(entity) == repr(entity)


class TestMissing:
    @staticmethod
    @pytest.mark.parametrize("optional", [True], indirect=True)
    def test_missing_when_optional(entity, data_dict):
        del data_dict["many"]
        assert entity.field.ids == []

    @staticmethod
    @pytest.mark.parametrize("optional", [False], indirect=True)
    def test_missing_when_required(entity, data_dict):
        del data_dict["many"]
        with pytest.raises(ValueError) as err:
            _ = entity.field
        assert str(err.value) == "Missing field: many"
