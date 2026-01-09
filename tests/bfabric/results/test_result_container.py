import polars.testing
import pytest
from logot import logged

from bfabric.results.result_container import ResultContainer


@pytest.fixture
def res1() -> ResultContainer:
    return ResultContainer([1, 2, 3], total_pages_api=1, errors=[])


@pytest.fixture
def res2() -> ResultContainer:
    return ResultContainer([4, 5], total_pages_api=1, errors=[])


@pytest.fixture
def res_with_empty() -> ResultContainer:
    return ResultContainer([{"a": None, "b": 1, "c": []}, {"a": 2, "b": 3, "c": None}], total_pages_api=None, errors=[])


def test_str(res1, res2):
    assert str(res1) == "[1, 2, 3]"
    assert str(res2) == "[4, 5]"


def test_repr(res1, res2):
    assert repr(res1) == "[1, 2, 3]"
    assert repr(res2) == "[4, 5]"


def test_iter(res1):
    items = list(iter(res1))
    assert items == [1, 2, 3]


def test_len(res1, res2):
    assert len(res1) == 3
    assert len(res2) == 2


def test_getitem(res1, res2):
    assert res1[0] == 1
    assert res1[1] == 2
    assert res1[2] == 3
    assert res2[0] == 4


def test_get_first_n_results_when_available(res1):
    res3 = res1.get_first_n_results(2)
    assert len(res3) == 2
    assert res3.results == [1, 2]


def test_get_first_n_results_when_not_available(res1):
    res3 = res1.get_first_n_results(4)
    assert len(res3) == 3
    assert res3.results == [1, 2, 3]


def test_get_first_n_results_when_none(res1):
    res3 = res1.get_first_n_results(None)
    assert len(res3) == 3
    assert res3.results == [1, 2, 3]


def test_assert_success_when_success(res1):
    res1.assert_success()


def test_assert_success_when_error(res1):
    res1.errors.append("MockedError")
    with pytest.raises(RuntimeError) as error:
        res1.assert_success()
    assert "Query was not successful" in str(error.value)


def test_extend_when_same_lengths():
    res_a = ResultContainer([{"a": 1}, {"a": 2}], total_pages_api=5, errors=[])
    res_b = ResultContainer([{"b": 3}, {"b": 4}], total_pages_api=5, errors=[])
    res_a.extend(res_b)
    assert len(res_a) == 4
    assert res_a.results == [{"a": 1}, {"a": 2}, {"b": 3}, {"b": 4}]
    assert res_a.total_pages_api == 5


def test_extend_when_different_lengths(res1, logot):
    res3 = ResultContainer(list(range(200, 400)), total_pages_api=2, errors=[])
    res3.extend(res1)

    assert len(res3) == 203
    assert res3.results == list(range(200, 400)) + [1, 2, 3]
    assert res3.total_pages_api == 2

    logot.assert_logged(logged.warning("Results observed with different total pages counts: 2 != 1"))


@pytest.mark.parametrize("case", ["default", "explicit"])
def test_to_list_dict_when_not_drop_empty(res_with_empty, case):
    expected = [{"a": None, "b": 1, "c": []}, {"a": 2, "b": 3, "c": None}]
    if case == "default":
        assert expected == res_with_empty.to_list_dict()
    if case == "explicit":
        assert expected == res_with_empty.to_list_dict(drop_empty=False)


def test_to_list_dict_when_drop_empty(res_with_empty):
    expected = [{"b": 1}, {"a": 2, "b": 3}]
    assert expected == res_with_empty.to_list_dict(drop_empty=True)


def test_to_polars(res1):
    df = res1.to_polars()
    polars.testing.assert_series_equal(polars.Series("column_0", [1, 2, 3]), df["column_0"])


def test_to_polars_flatten_relations():
    res = ResultContainer(
        [{"a": 1, "nested": {"x": 10, "y": 20}}, {"a": 2, "nested": {"x": 30, "y": 40}}],
        total_pages_api=None,
        errors=[],
    )
    df = res.to_polars(flatten=True)
    polars.testing.assert_series_equal(polars.Series("a", [1, 2]), df["a"])
    polars.testing.assert_series_equal(polars.Series("nested_x", [10, 30]), df["nested_x"])
    polars.testing.assert_series_equal(polars.Series("nested_y", [20, 40]), df["nested_y"])
    assert "nested" not in df.columns
