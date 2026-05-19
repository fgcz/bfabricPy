from __future__ import annotations

import polars as pl
from polars.exceptions import InvalidOperationError
from pydantic import BaseModel, field_validator


class DatasetChanges(BaseModel):
    """Model representing changes between two datasets.

    The main purpose is to identify whether a change is present (`__bool__` can be used),
    and notify a user about what has changed at a very basic level.
    """

    column_position: list[str] = []
    """List of columns whose position has changed."""

    column_added: list[str] = []
    """List of columns added to the dataframe."""

    column_removed: list[str] = []
    """List of columns removed from the dataframe."""

    row_count: tuple[int, int] | None = None
    """Tuple of (row count old, row count new) when the number of rows has changed."""

    changed_values: list[str] = []
    """List of columns with changed values."""

    def __bool__(self) -> bool:
        """Return True if there are any changes."""
        return (
            bool(self.changed_values)
            or bool(self.column_added)
            or bool(self.column_removed)
            or bool(self.column_position)
            or self.row_count is not None
        )

    @field_validator("row_count")
    @classmethod
    def _row_count(cls, value: tuple[int, int] | None) -> tuple[int, int] | None:
        if value is not None:
            if value[0] == value[1]:
                raise ValueError("When the tuple is set, it must be two distinct values")
            if value[0] < 0 or value[1] < 0:
                raise ValueError("Row counts must be non-negative")
        return value


def identify_changes(old_df: pl.DataFrame, new_df: pl.DataFrame) -> DatasetChanges:
    """Identify the changes from `old_df` to `new_df`."""
    changes = DatasetChanges()

    changes.column_added = sorted(set(new_df.columns) - set(old_df.columns))
    changes.column_removed = sorted(set(old_df.columns) - set(new_df.columns))

    common_columns = set(new_df.columns) & set(old_df.columns)
    changes.column_position = sorted(
        column for column in common_columns if new_df.columns.index(column) != old_df.columns.index(column)
    )

    if len(old_df) != len(new_df):
        changes.row_count = len(old_df), len(new_df)

    for column_name in new_df.columns:
        if column_name in changes.column_added:
            continue
        if new_df[column_name].equals(old_df[column_name]):
            continue

        try:
            if new_df[column_name].cast(pl.Utf8).equals(old_df[column_name].cast(pl.Utf8)):
                continue
        except InvalidOperationError:
            pass

        changes.changed_values.append(column_name)

    return changes
