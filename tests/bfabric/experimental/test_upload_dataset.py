import polars as pl
from logot import Logot, logged

from bfabric.experimental.upload_dataset import warn_on_trailing_spaces


def test_warn_on_trailing_spaces_when_no(logot: Logot):
    table = pl.DataFrame({"a": ["a", "b"], "b": ["a", "b"], "c": [1, 2]})
    warn_on_trailing_spaces(table)
    logot.assert_not_logged(logged.warning("%s"))


def test_warn_on_trailing_spaces_when_warning(logot):
    table = pl.DataFrame({"a": ["a", "b"], "b": ["a", "b "], "c": [1, 2]})
    warn_on_trailing_spaces(table)
    logot.assert_logged(logged.warning("Warning: Column 'b' contains trailing spaces."))
