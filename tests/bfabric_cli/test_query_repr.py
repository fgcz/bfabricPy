import pytest

from bfabric_scripts.cli.api.query_repr import Query


@pytest.fixture
def input_without_duplicates():
    return ["a", "x", "b", "y", "c", "z"]


@pytest.fixture
def input_with_duplicates():
    return ["a", "x", "b", "y", "a", "z"]


@pytest.mark.parametrize("duplicates_method", ["drop", "collect", "error"])
def test_to_dict_when_no_duplicates(input_without_duplicates, duplicates_method):
    query = Query(input_without_duplicates)
    assert query.to_dict(duplicates_method) == {"a": "x", "b": "y", "c": "z"}


def test_to_dict_when_duplicates_drop(input_with_duplicates):
    query = Query(input_with_duplicates)
    assert query.to_dict("drop") == {"a": "z", "b": "y"}


def test_to_dict_when_duplicates_collect(input_with_duplicates):
    query = Query(input_with_duplicates)
    assert query.to_dict("collect") == {"a": ["x", "z"], "b": "y"}


def test_to_dict_when_duplicates_error(input_with_duplicates):
    query = Query(input_with_duplicates)
    with pytest.raises(ValueError) as error:
        query.to_dict("error")
    assert "Duplicate keys found in query: ['a']" in str(error.value)


def test_drop_key_inplace(input_without_duplicates):
    query = Query(input_without_duplicates)
    query.drop_key_inplace("b")
    assert query.root == [("a", "x"), ("c", "z")]
