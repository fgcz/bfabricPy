import polars as pl
import pytest
from logot import Logot, logged

from bfabric.operations.dataset import check_for_invalid_characters, warn_on_trailing_spaces


def test_warn_on_trailing_spaces_when_no(logot: Logot):
    table = pl.DataFrame({"a": ["a", "b"], "b": ["a", "b"], "c": [1, 2]})
    warn_on_trailing_spaces(table)
    logot.assert_not_logged(logged.warning("%s"))


def test_warn_on_trailing_spaces_when_warning(logot):
    table = pl.DataFrame({"a": ["a", "b"], "b": ["a", "b "], "c": [1, 2]})
    warn_on_trailing_spaces(table)
    logot.assert_logged(logged.warning("Warning: Column 'b' contains trailing spaces."))


def test_check_for_invalid_characters_clean():
    table = pl.DataFrame({"a": ["a", "b"], "b": [1, 2]})
    check_for_invalid_characters(table, ",\t")


def test_check_for_invalid_characters_dirty():
    table = pl.DataFrame({"a": ["x,y", "b"], "b": ["fine", "ok"]})
    with pytest.raises(RuntimeError, match=r"Invalid characters found in columns: \['a'\]"):
        check_for_invalid_characters(table, ",")


def test_check_for_invalid_characters_multiple_columns():
    table = pl.DataFrame(
        {
            "col1": ["abc", "d!ef", "ghi"],
            "col2": ["123", "45@6", "789"],
            "col3": ["xyz", "uvw", "rst"],
        }
    )
    with pytest.raises(RuntimeError, match=r"Invalid characters found in columns: \['col1', 'col2'\]"):
        check_for_invalid_characters(table, "!@#")


def test_check_for_invalid_characters_empty_chars_skips():
    table = pl.DataFrame({"a": ["x,y", "b"]})
    check_for_invalid_characters(table, "")


def test_check_for_invalid_characters_empty_dataframe():
    check_for_invalid_characters(pl.DataFrame(), "!@#")


def test_check_for_invalid_characters_non_string_columns():
    table = pl.DataFrame({"col1": [1, 2, 3], "col2": [4.5, 5.6, 6.7], "col3": ["abc", "def", "ghi"]})
    check_for_invalid_characters(table, "!@#")
