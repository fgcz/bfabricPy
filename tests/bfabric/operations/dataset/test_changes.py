import polars as pl
import pytest
from pydantic import ValidationError

from bfabric.operations.dataset import DatasetChanges, identify_changes


def test_no_changes():
    df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    changes = identify_changes(df, df)
    assert not changes


def test_column_added():
    old = pl.DataFrame({"a": [1, 2]})
    new = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    changes = identify_changes(old, new)
    assert changes.column_added == ["b"]
    assert bool(changes)


def test_column_removed():
    old = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    new = pl.DataFrame({"a": [1, 2]})
    changes = identify_changes(old, new)
    assert changes.column_removed == ["b"]


def test_column_position():
    old = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    new = pl.DataFrame({"b": ["x", "y"], "a": [1, 2]})
    changes = identify_changes(old, new)
    assert changes.column_position == ["a", "b"]


def test_changed_values():
    old = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    new = pl.DataFrame({"a": [1, 2], "b": ["x", "z"]})
    changes = identify_changes(old, new)
    assert changes.changed_values == ["b"]


def test_row_count():
    old = pl.DataFrame({"a": [1, 2]})
    new = pl.DataFrame({"a": [1, 2, 3]})
    changes = identify_changes(old, new)
    assert changes.row_count == (2, 3)


def test_row_count_validator_rejects_equal():
    with pytest.raises(ValidationError):
        DatasetChanges(row_count=(3, 3))


def test_row_count_validator_rejects_negative():
    with pytest.raises(ValidationError):
        DatasetChanges(row_count=(-1, 2))


def test_cast_to_string_treated_as_unchanged():
    old = pl.DataFrame({"a": [1, 2]})
    new = pl.DataFrame({"a": ["1", "2"]})
    changes = identify_changes(old, new)
    assert changes.changed_values == []
