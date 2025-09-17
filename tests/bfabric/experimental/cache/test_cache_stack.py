import pytest

from bfabric.experimental.cache._entity_cache import EntityCache
from bfabric.experimental.cache.cache_stack import CacheStack


@pytest.fixture
def mock_cache_1(mocker):
    return mocker.MagicMock(name="mock_cache_1", spec=EntityCache, autospec=True)


@pytest.fixture
def mock_cache_2(mocker):
    return mocker.MagicMock(name="mock_cache_2", spec=EntityCache, autospec=True)


class TestEmpty:
    @pytest.fixture
    def stack(self):
        return CacheStack()

    def test_cache_pop(self, stack):
        with pytest.raises(IndexError) as error:
            assert stack.cache_pop() is None
        assert "pop from empty list" in str(error.value)

    def test_item_contains(self, stack, mock_cache_1):
        assert not stack.item_contains("Entity1", 1)

    def test_item_get(self, stack, mock_cache_1):
        assert stack.item_get("Entity1", 1) is None

    def test_item_put(self, stack, mock_cache_1):
        stack.item_put("Entity1", 1, "entity1")


class TestPopulated:
    @pytest.fixture
    def stack(self, mock_cache_1, mock_cache_2):
        result = CacheStack()
        result.cache_push(mock_cache_1)
        result.cache_push(mock_cache_2)
        return result

    def test_item_contains_when_exists_in_cache_1(self, stack, mock_cache_1, mock_cache_2):
        mock_cache_1.contains.return_value = True
        mock_cache_2.contains.return_value = False
        assert stack.item_contains("Entity1", 1)
        mock_cache_1.contains.assert_called_once_with("Entity1", 1)
        mock_cache_2.contains.assert_called_once_with("Entity1", 1)

    def test_item_contains_when_exists_in_cache_2(self, stack, mock_cache_1, mock_cache_2):
        mock_cache_1.contains.return_value = False
        mock_cache_2.contains.return_value = True
        assert stack.item_contains("Entity1", 1)
        mock_cache_1.contains.assert_not_called()
        mock_cache_2.contains.assert_called_once_with("Entity1", 1)

    def test_item_contains_when_not_exists(self, stack, mock_cache_1, mock_cache_2):
        mock_cache_1.contains.return_value = False
        mock_cache_2.contains.return_value = False
        assert not stack.item_contains("Entity1", 1)
        mock_cache_1.contains.assert_called_once_with("Entity1", 1)
        mock_cache_2.contains.assert_called_once_with("Entity1", 1)

    def test_item_get_when_exists_in_cache_1(self, stack, mock_cache_1, mock_cache_2):
        mock_cache_1.get.return_value = "entity1"
        mock_cache_2.get.return_value = None
        assert stack.item_get("Entity1", 1) == "entity1"
        mock_cache_1.get.assert_called_once_with("Entity1", 1)

    def test_item_get_when_exists_in_cache_2(self, stack, mock_cache_1, mock_cache_2):
        mock_cache_1.get.return_value = None
        mock_cache_2.get.return_value = "entity1"
        assert stack.item_get("Entity1", 1) == "entity1"
        mock_cache_2.get.assert_called_once_with("Entity1", 1)

    def test_item_put(self, stack, mock_cache_1, mock_cache_2):
        stack.item_put("Entity1", 1, "entity1")
        mock_cache_1.put.assert_called_once_with("Entity1", 1, "entity1")
        mock_cache_2.put.assert_called_once_with("Entity1", 1, "entity1")
