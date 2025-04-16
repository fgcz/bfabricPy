from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl
from loguru import logger

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric


def polars_to_bfabric_type(dtype: pl.DataType) -> str | None:
    """Returns the B-Fabric type for a given Polars data type, defaulting to String if no correspondence is found."""
    if str(dtype).startswith("Int"):
        return "Integer"
    elif str(dtype).startswith("String"):
        return "String"
    else:
        return "String"


def polars_to_bfabric_dataset(
    data: pl.DataFrame,
) -> dict[str, list[dict[str, int | str | float]]]:
    """Converts a Polars DataFrame to a B-Fabric dataset representation."""
    attributes = [
        {
            "name": col,
            "position": i + 1,
            "type": polars_to_bfabric_type(data[col].dtype),
        }
        for i, col in enumerate(data.columns)
    ]
    items = [
        {
            "field": [{"attributeposition": i_field + 1, "value": value} for i_field, value in enumerate(row)],
            "position": i_row + 1,
        }
        for i_row, row in enumerate(data.iter_rows())
    ]
    return {"attribute": attributes, "item": items}


def bfabric_save_csv2dataset(
    client: Bfabric,
    csv_file: Path,
    dataset_name: str,
    container_id: int,
    workunit_id: int | None,
    sep: str,
    has_header: bool,
    invalid_characters: str,
) -> None:
    """Creates a dataset in B-Fabric from a csv file."""
    data = pl.read_csv(csv_file, separator=sep, has_header=has_header, infer_schema_length=None)
    check_for_invalid_characters(data=data, invalid_characters=invalid_characters)
    obj = polars_to_bfabric_dataset(data)
    obj["name"] = dataset_name
    obj["containerid"] = container_id
    if workunit_id is not None:
        obj["workunitid"] = workunit_id
    endpoint = "dataset"
    res = client.save(endpoint=endpoint, obj=obj)
    print(res.to_list_dict()[0])


def check_for_invalid_characters(data: pl.DataFrame, invalid_characters: str) -> None:
    """Raises a RuntimeError if any cell in the DataFrame contains an invalid character."""
    if not invalid_characters:
        return
    invalid_columns_df = data.select(pl.col(pl.String).str.contains_any(list(invalid_characters)).any())
    if invalid_columns_df.is_empty():
        return
    invalid_columns = (
        invalid_columns_df.transpose(include_header=True, header_name="column")
        .filter(pl.col("column_0"))["column"]
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
