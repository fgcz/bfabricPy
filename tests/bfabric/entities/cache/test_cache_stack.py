import pytest

from bfabric.entities.core.uri import EntityUri
from bfabric.entities.cache._cache_stack import CacheStack
from bfabric.entities.cache._entity_memory_cache import EntityMemoryCache


@pytest.fixture
def mock_cache_1(mocker):
    return mocker.MagicMock(name="mock_cache_1", spec=EntityMemoryCache, autospec=True)


@pytest.fixture
def mock_cache_2(mocker):
    return mocker.MagicMock(name="mock_cache_2", spec=EntityMemoryCache, autospec=True)


@pytest.fixture
def uri1():
    return EntityUri("https://bfabric.example.com/bfabric/project/show.html?id=1")


@pytest.fixture
def uri2():
    return EntityUri("https://bfabric.example.com/bfabric/project/show.html?id=2")


@pytest.fixture
def uri3():
    return EntityUri("https://bfabric.example.com/bfabric/project/show.html?id=3")


@pytest.fixture
def uri4():
    return EntityUri("https://bfabric.example.com/bfabric/project/show.html?id=4")


class TestEmpty:
    @pytest.fixture
    def stack(self):
        return CacheStack()

    def test_cache_pop(self, stack):
        with pytest.raises(IndexError) as error:
            assert stack.cache_pop() is None
        assert "pop from empty list" in str(error.value)

    def test_item_contains(self, stack, uri1):
        assert not stack.item_contains(uri1)

    def test_item_get(self, stack, uri1):
        assert stack.item_get(uri1) is None

    def test_item_get_all(self, stack, uri1, uri2, uri3):
        assert stack.item_get_all([uri1, uri2, uri3]) == {}

    def test_item_put(self, stack, mocker, uri1):
        entity1 = mocker.Mock(uri=uri1, id=1)
        stack.item_put(entity1)

    def test_item_put_all(self, stack, mocker, uri1, uri2):
        entity1 = mocker.Mock(uri=uri1, id=1)
        entity2 = mocker.Mock(uri=uri2, id=2)
        stack.item_put_all([entity1, entity2])


class TestPopulated:
    @pytest.fixture
    def stack(self, mock_cache_1, mock_cache_2):
        result = CacheStack()
        result.cache_push(mock_cache_1)
        result.cache_push(mock_cache_2)
        return result

    def test_item_contains_when_exists_in_cache_1(self, stack, mock_cache_1, mock_cache_2, uri1):
        mock_cache_1.contains.return_value = True
        mock_cache_2.contains.return_value = False
        assert stack.item_contains(uri1)
        mock_cache_1.contains.assert_called_once_with(uri1)
        mock_cache_2.contains.assert_called_once_with(uri1)

    def test_item_contains_when_exists_in_cache_2(self, stack, mock_cache_1, mock_cache_2, uri1):
        mock_cache_1.contains.return_value = False
        mock_cache_2.contains.return_value = True
        assert stack.item_contains(uri1)
        mock_cache_1.contains.assert_not_called()
        mock_cache_2.contains.assert_called_once_with(uri1)

    def test_item_contains_when_not_exists(self, stack, mock_cache_1, mock_cache_2, uri1):
        mock_cache_1.contains.return_value = False
        mock_cache_2.contains.return_value = False
        assert not stack.item_contains(uri1)
        mock_cache_1.contains.assert_called_once_with(uri1)
        mock_cache_2.contains.assert_called_once_with(uri1)

    def test_item_get_when_exists_in_cache_1(self, stack, mock_cache_1, mock_cache_2, mocker, uri1):
        entity1 = mocker.Mock(uri=uri1, id=1)
        mock_cache_1.get.return_value = entity1
        mock_cache_2.get.return_value = None
        assert stack.item_get(uri1) == entity1
        mock_cache_1.get.assert_called_once_with(uri1)

    def test_item_get_when_exists_in_cache_2(self, stack, mock_cache_1, mock_cache_2, mocker, uri1):
        entity1 = mocker.Mock(uri=uri1, id=1)
        mock_cache_1.get.return_value = None
        mock_cache_2.get.return_value = entity1
        assert stack.item_get(uri1) == entity1
        mock_cache_2.get.assert_called_once_with(uri1)

    def test_item_get_all(self, stack, mock_cache_1, mock_cache_2, mocker, uri1, uri2, uri3, uri4):
        entity1 = mocker.Mock(uri=uri1, id=1)
        entity2 = mocker.Mock(uri=uri2, id=2)
        entity3 = mocker.Mock(uri=uri3, id=3)
        mock_cache_1.get_all.return_value = {uri1: entity1, uri2: entity2}
        mock_cache_2.get_all.return_value = {uri3: entity3}
        result = stack.item_get_all([uri1, uri2, uri3, uri4])
        assert result == {uri1: entity1, uri2: entity2, uri3: entity3}
        # cache_2 is checked first (reversed stack), gets called with all URIs (order not guaranteed due to set)
        assert set(mock_cache_2.get_all.call_args[0][0]) == {uri1, uri2, uri3, uri4}
        # cache_1 is checked second, gets called with URIs not found in cache_2 (order not guaranteed due to set)
        assert set(mock_cache_1.get_all.call_args[0][0]) == {uri1, uri2, uri4}

    def test_item_put(self, stack, mock_cache_1, mock_cache_2, mocker, uri1):
        entity1 = mocker.Mock(uri=uri1, id=1)
        stack.item_put(entity1)
        mock_cache_1.put.assert_called_once_with(entity1)
        mock_cache_2.put.assert_called_once_with(entity1)

    def test_item_put_all(self, stack, mock_cache_1, mock_cache_2, mocker, uri1, uri2):
        entity1 = mocker.Mock(uri=uri1, id=1)
        entity2 = mocker.Mock(uri=uri2, id=2)
        entities = [entity1, entity2]
        stack.item_put_all(entities)
        mock_cache_1.put.assert_any_call(entity1)
        mock_cache_1.put.assert_any_call(entity2)
        mock_cache_2.put.assert_any_call(entity1)
        mock_cache_2.put.assert_any_call(entity2)
        assert mock_cache_1.put.call_count == 2
        assert mock_cache_2.put.call_count == 2
