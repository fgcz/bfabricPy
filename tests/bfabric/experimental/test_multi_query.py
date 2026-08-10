import pytest

from bfabric.bfabric import Bfabric
from bfabric.experimental.multi_query import MultiQuery, _count_query_elements
from bfabric.results.result_container import ResultContainer


@pytest.fixture
def mock_client(mocker):
    client = mocker.MagicMock(name="mock_client", spec=Bfabric)
    client.read.side_effect = lambda *args, **kwargs: ResultContainer([], total_pages_api=1, errors=[])
    return client


@pytest.fixture
def multi_query(mock_client):
    return MultiQuery(client=mock_client)


class TestReadMulti:
    def test_chunks_leave_room_for_other_query_fields(self, mocker, mock_client, multi_query):
        values = list(range(100))
        multi_query.read_multi("importresource", {"containerid": 5}, "relativepath", values)
        assert mock_client.read.mock_calls == [
            mocker.call(
                "importresource",
                {"containerid": 5, "relativepath": values[:99]},
                max_results=None,
                return_id_only=False,
            ),
            mocker.call(
                "importresource",
                {"containerid": 5, "relativepath": values[99:]},
                max_results=None,
                return_id_only=False,
            ),
        ]

    def test_single_request_for_full_chunk_without_other_fields(self, mocker, mock_client, multi_query):
        values = list(range(100))
        multi_query.read_multi("project", {}, "id", values)
        assert mock_client.read.mock_calls == [
            mocker.call("project", {"id": values}, max_results=None, return_id_only=False)
        ]

    def test_list_valued_field_reserves_one_element_per_value(self, mock_client, multi_query):
        values = list(range(100))
        multi_query.read_multi("resource", {"workunitid": [1, 2, 3]}, "id", values)
        sent = [call.args[1]["id"] for call in mock_client.read.mock_calls]
        assert sent == [values[:97], values[97:]]

    def test_multi_query_key_in_obj_reserves_nothing(self, mock_client, multi_query):
        values = list(range(100))
        multi_query.read_multi("project", {"id": [1, 2, 3]}, "id", values)
        sent = [call.args[1]["id"] for call in mock_client.read.mock_calls]
        assert sent == [values]

    def test_raises_when_query_leaves_no_room(self, mock_client, multi_query):
        with pytest.raises(ValueError, match="already use 100 of the 100 query elements"):
            multi_query.read_multi("importresource", {"containerid": list(range(100))}, "relativepath", ["a"])
        mock_client.read.assert_not_called()

    def test_does_not_mutate_the_caller_query(self, multi_query):
        obj = {"containerid": 5}
        multi_query.read_multi("importresource", obj, "relativepath", list(range(150)))
        assert obj == {"containerid": 5}

    def test_no_values_makes_no_requests(self, mock_client, multi_query):
        result = multi_query.read_multi("project", {}, "id", [])
        mock_client.read.assert_not_called()
        assert len(result) == 0

    def test_concatenates_results_across_chunks(self, mock_client, multi_query):
        mock_client.read.side_effect = lambda endpoint, query, **kwargs: ResultContainer(
            [{"id": value} for value in query["id"][:1]], total_pages_api=1, errors=[]
        )
        result = multi_query.read_multi("project", {}, "id", list(range(150)))
        assert result.results == [{"id": 0}, {"id": 100}]
        assert result.total_pages_api is None

    def test_forwards_return_id_only(self, mock_client, multi_query):
        multi_query.read_multi("project", {}, "id", [1], return_id_only=True)
        assert mock_client.read.mock_calls[0].kwargs["return_id_only"]


class TestCountQueryElements:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (5, 1),
            ("abc", 1),
            (None, 1),
            (False, 1),
            ([1, 2, 3], 3),
            ({}, 0),
            ({"a": 1, "b": 2}, 2),
            ({"a": [1, 2]}, 2),
            ([{"a": 1, "b": 2}], 2),
        ],
    )
    def test_count(self, value, expected):
        assert _count_query_elements(value) == expected
