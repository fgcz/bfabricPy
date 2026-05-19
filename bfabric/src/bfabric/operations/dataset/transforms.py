from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from bfabric.operations.dataset._column_types import DatasetColumnTypes, get_dataset_column_types

if TYPE_CHECKING:
    from bfabric.typing import ApiRequestDataType


def _all_values_are_integers(col: pl.Series) -> bool:
    dtype = col.dtype
    if dtype.is_integer():
        return True
    elif isinstance(dtype, pl.String):
        int_col = col.str.to_integer(strict=False)
        return int_col.null_count() == 0
    else:
        return False


def _polars_column_to_bfabric_type(
    dataframe: pl.DataFrame,
    column_name: str,
    column_types: DatasetColumnTypes | None = None,
) -> str:
    """Returns the B-Fabric type for a given Polars column name."""
    if column_types is not None:
        entity_lookup = {entity.lower(): entity for entity in column_types.entities}
        if column_name.lower() in entity_lookup and _all_values_are_integers(dataframe[column_name]):
            return entity_lookup[column_name.lower()]

    dtype = dataframe[column_name].dtype
    if dtype.is_integer():
        return "Integer"
    return "String"


def polars_to_dataset_dict(data: pl.DataFrame) -> dict[str, ApiRequestDataType]:
    """Converts a Polars DataFrame to a B-Fabric dataset payload dict (attributes + items)."""
    column_types = get_dataset_column_types()
    attributes: list[ApiRequestDataType] = [
        {
            "name": col,
            "position": i + 1,
            "type": _polars_column_to_bfabric_type(data, column_name=col, column_types=column_types),
        }
        for i, col in enumerate(data.columns)
    ]
    items: list[ApiRequestDataType] = [
        {
            "field": [
                {"attributeposition": i_field + 1, "value": value}
                for i_field, value in enumerate(row)  # pyright: ignore[reportAny]
            ],
            "position": i_row + 1,
        }
        for i_row, row in enumerate(data.iter_rows())
    ]
    return {"attribute": attributes, "item": items}
