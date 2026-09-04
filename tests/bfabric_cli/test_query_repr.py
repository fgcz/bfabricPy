import pytest

from bfabric_scripts.cli.api.query_repr import Query


@pytest.fixture
def input_without_duplicates():
    return ["a", "x", "b", "y", "c", "z"]


@pytest.fixture
def input_with_duplicates():
    return ["a", "x", "b", "y", "a", "z"]


@pytest.mark.parametrize("duplicates_method", ["collect", "error"])
def test_to_dict_when_no_duplicates(input_without_duplicates, duplicates_method):
    query = Query.model_validate(input_without_duplicates)
    assert query.to_dict(duplicates_method) == {"a": "x", "b": "y", "c": "z"}


def test_to_dict_when_duplicates_collect(input_with_duplicates):
    query = Query.model_validate(input_with_duplicates)
    assert query.to_dict("collect") == {"a": ["x", "z"], "b": "y"}


def test_to_dict_when_duplicates_error(input_with_duplicates):
    query = Query.model_validate(input_with_duplicates)
    with pytest.raises(ValueError) as error:
        query.to_dict("error")
    assert "Duplicate keys found in query: ['a']" in str(error.value)


def test_drop_key_inplace(input_without_duplicates):
    query = Query.model_validate(input_without_duplicates)
    query.drop_key_inplace("b")
    assert query.pairs == [("a", "x"), ("c", "z")]


class TestJsonInput:
    def test_json_is_merged_with_pairs(self):
        query = Query.model_validate({"pairs": ["name", "x"], "json_input": '{"containerid": 1234}'})
        assert query.to_dict("error") == {"name": "x", "containerid": 1234}

    def test_json_keeps_nested_and_typed_values(self):
        query = Query(json_input='{"container": {"id": 7}, "tags": [1, 2], "active": true}')
        assert query.to_dict("error") == {"container": {"id": 7}, "tags": [1, 2], "active": True}

    def test_json_file_is_read_and_json_wins(self, tmp_path):
        path = tmp_path / "attributes.json"
        _ = path.write_text('{"name": "from-file", "other": 1}')
        query = Query(json_input='{"name": "from-flag"}', json_file=path)
        assert query.to_dict("error") == {"name": "from-flag", "other": 1}

    @pytest.mark.parametrize("payload", ["[1, 2]", '"scalar"'])
    def test_json_that_is_not_an_object_raises(self, payload):
        with pytest.raises(ValueError, match="JSON input must be an object"):
            Query(json_input=payload).to_dict("error")

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError):
            Query(json_input="{oops").to_dict("error")

    @pytest.mark.parametrize("duplicates", ["collect", "error"])
    def test_key_in_both_pairs_and_json_raises(self, duplicates):
        query = Query.model_validate({"pairs": ["name", "x"], "json_input": '{"name": "y"}'})
        with pytest.raises(ValueError, match="both as pairs and in JSON input"):
            query.to_dict(duplicates)
