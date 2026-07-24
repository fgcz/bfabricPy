import polars as pl
import polars.testing
import pytest
from polars.exceptions import DuplicateError

from bfabric.utils.polars_utils import flatten_relations


def test_flatten_relations():
    df = pl.DataFrame(
        {
            "a": [1, 2, 3],
            "b": [{"x": 10, "y": 11}, {"x": 20, "y": 21}, {"x": 30, "y": 31}],
        }
    )
    flatten_relations(df)
    expected_df = pl.DataFrame(
        {
            "a": [1, 2, 3],
            "b_x": [10, 20, 30],
            "b_y": [11, 21, 31],
        }
    )
    pl.testing.assert_frame_equal(flatten_relations(df), expected_df)


def test_flatten_relations_nested_struct():
    df = pl.DataFrame(
        {
            "a": [1, 2],
            "b": [{"x": 10, "inner": {"p": 100, "q": 101}}, {"x": 20, "inner": {"p": 200, "q": 201}}],
        }
    )
    expected_df = pl.DataFrame(
        {
            "a": [1, 2],
            "b_x": [10, 20],
            "b_inner_p": [100, 200],
            "b_inner_q": [101, 201],
        }
    )
    pl.testing.assert_frame_equal(flatten_relations(df), expected_df)


def test_flatten_relations_empty_df():
    df = pl.DataFrame({"a": [], "b": []})
    pl.testing.assert_frame_equal(flatten_relations(df), df)


def test_flatten_relations_naming_conflict():
    df = pl.DataFrame({"b_a": [1], "b": [{"a": 10}]})
    with pytest.raises(DuplicateError):
        flatten_relations(df)
