import polars as pl
from logot import Logot, logged

from bfabric.operations.dataset import warn_on_trailing_spaces


def test_warn_on_trailing_spaces_when_no(logot: Logot):
    table = pl.DataFrame({"a": ["a", "b"], "b": ["a", "b"], "c": [1, 2]})
    warn_on_trailing_spaces(table)
    logot.assert_not_logged(logged.warning("%s"))


def test_warn_on_trailing_spaces_when_warning(logot):
    table = pl.DataFrame({"a": ["a", "b"], "b": ["a", "b "], "c": [1, 2]})
    warn_on_trailing_spaces(table)
    logot.assert_logged(logged.warning("Warning: Column 'b' contains trailing spaces."))


def test_check_for_invalid_characters_clean():
    from bfabric.operations.dataset import check_for_invalid_characters

    table = pl.DataFrame({"a": ["a", "b"], "b": [1, 2]})
    check_for_invalid_characters(table, ",\t")


def test_check_for_invalid_characters_dirty():
    import pytest

    from bfabric.operations.dataset import check_for_invalid_characters

    table = pl.DataFrame({"a": ["x,y", "b"], "b": ["fine", "ok"]})
    with pytest.raises(RuntimeError, match="Invalid characters found in columns:"):
        check_for_invalid_characters(table, ",")


def test_check_for_invalid_characters_empty_chars_skips():
    table = pl.DataFrame({"a": ["x,y", "b"]})
    # empty invalid_characters should not raise
    from bfabric.operations.dataset import check_for_invalid_characters

    check_for_invalid_characters(table, "")
