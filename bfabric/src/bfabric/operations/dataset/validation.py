from __future__ import annotations

import polars as pl
from loguru import logger


def check_for_invalid_characters(data: pl.DataFrame, invalid_characters: str) -> None:
    """Raises a RuntimeError if any cell in the DataFrame contains an invalid character."""
    if not invalid_characters:
        return
    invalid_columns_df = data.select(  # pyright: ignore[reportUnknownMemberType]
        pl.col(pl.String).str.contains_any(list(invalid_characters)).any()  # pyright: ignore[reportUnknownMemberType]
    )
    if invalid_columns_df.is_empty():
        return
    invalid_columns = (
        invalid_columns_df.transpose(include_header=True, header_name="column")
        .filter(pl.col("column_0"))["column"]  # pyright: ignore[reportUnknownMemberType]
        .to_list()
    )
    if invalid_columns:
        raise RuntimeError(f"Invalid characters found in columns: {invalid_columns}")


def warn_on_trailing_spaces(table: pl.DataFrame) -> None:
    """Logs warnings when trailing spaces are detected in any of the string columns of the provided table."""
    for column in table.columns:
        if not isinstance(table[column].dtype, pl.String):
            continue
        if table[column].str.contains(r"\s+$").any():
            logger.warning(f"Warning: Column '{column}' contains trailing spaces.")
