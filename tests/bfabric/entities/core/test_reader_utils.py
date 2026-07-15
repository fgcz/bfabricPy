import pytest

from bfabric.entities.core.reader_utils import entities_by_id, present_entities
from bfabric.entities.core.uri import EntityUri


@pytest.fixture
def uri(bfabric_instance):
    def _make(entity_id: int, entity_type: str = "resource") -> EntityUri:
        return EntityUri(f"{bfabric_instance}{entity_type}/show.html?id={entity_id}")

    return _make


class TestEntitiesById:
    def test_rekeys_by_int_id(self, mocker, uri):
        a, b = mocker.MagicMock(name="a"), mocker.MagicMock(name="b")
        result = entities_by_id({uri(1): a, uri(2): b})
        assert result == {1: a, 2: b}

    def test_drops_missing_entries(self, mocker, uri):
        found = mocker.MagicMock(name="found")
        result = entities_by_id({uri(1): found, uri(2): None})
        assert result == {1: found}

    def test_empty_input(self):
        assert entities_by_id({}) == {}

    def test_all_missing(self, uri):
        assert entities_by_id({uri(1): None, uri(2): None}) == {}


class TestPresentEntities:
    def test_drops_missing_and_preserves_order(self, mocker, uri):
        a, b = mocker.MagicMock(name="a"), mocker.MagicMock(name="b")
        result = present_entities({uri(1): a, uri(2): None, uri(3): b})
        assert result == [a, b]

    def test_empty_input(self):
        assert present_entities({}) == []

    def test_all_missing(self, uri):
        assert present_entities({uri(1): None, uri(2): None}) == []
