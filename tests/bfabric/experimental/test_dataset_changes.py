from polars.interchange import column
import pytest
import polars as pl
from bfabric.experimental.dataset_changes import identify_changes, DatasetChanges


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, False),
        ({"column_position": ["a"]}, True),
        ({"column_added": ["a"]}, True),
        ({"column_removed": ["a"]}, True),
        ({"row_count": (1, 2)}, True),
        ({"changed_values": ["a"]}, True),
    ],
)
def test_bool(kwargs, expected):
    changes = DatasetChanges(**kwargs)
    assert bool(changes) == expected


class TestIdentifyChanges:
    @pytest.fixture
    def old_df(self):
        return pl.DataFrame({"A": [1, 2, 3], "b": [4, 5, 6]})

    def test_no_changes(self, old_df):
        new_df = old_df.clone()
        changes = identify_changes(old_df, new_df)
        assert changes == DatasetChanges(
            column_position=[], column_added=[], column_removed=[], row_count=None, changed_values=[]
        )

    def test_column_position(self, old_df):
        new_df = old_df.select("b", "A").clone()
        changes = identify_changes(old_df, new_df)
        assert changes == DatasetChanges(
            column_position=["A", "b"], column_added=[], column_removed=[], row_count=None, changed_values=[]
        )

    def test_column_add(self, old_df):
        new_df = old_df.with_columns(x=pl.lit("x"))
        changes = identify_changes(old_df, new_df)
        assert changes == DatasetChanges(
            column_position=[], column_added=["x"], column_removed=[], row_count=None, changed_values=[]
        )

    def test_column_remove(self, old_df):
        new_df = old_df.drop("A")
        changes = identify_changes(old_df, new_df)
        assert changes == DatasetChanges(
            column_position=["b"], column_added=[], column_removed=["A"], row_count=None, changed_values=[]
        )

    def test_add_row(self, old_df):
        new_df = pl.DataFrame({"A": [1, 2, 3, 10], "b": [4, 5, 6, 10]})
        changes = identify_changes(old_df, new_df)
        assert changes == DatasetChanges(
            column_position=[], column_added=[], column_removed=[], row_count=(3, 4), changed_values=["A", "b"]
        )

    def test_remove_row(self, old_df):
        new_df = old_df.head(1)
        changes = identify_changes(old_df, new_df)
        assert changes == DatasetChanges(
            column_position=[], column_added=[], column_removed=[], row_count=(3, 1), changed_values=["A", "b"]
        )

    def test_change_values(self, old_df):
        new_df = pl.DataFrame({"A": [1, 2, 3], "b": [4, 5, 5]})
        changes = identify_changes(old_df, new_df)
        assert changes == DatasetChanges(
            column_position=[], column_added=[], column_removed=[], row_count=None, changed_values=["b"]
        )
