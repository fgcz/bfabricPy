from __future__ import annotations

from typing import TYPE_CHECKING, assert_never

import polars as pl

if TYPE_CHECKING:
    from pathlib import Path

    from bfabric_app_runner.specs.outputs.annotations import BfabricOutputDataset, IncludeDatasetRef, IncludeResourceRef


def _validate_table_schema(df: pl.DataFrame) -> None:
    """Validate that required columns exist and have correct types."""
    if "Resource" not in df.columns:
        raise ValueError("Missing required column: Resource")

    if not df["Resource"].dtype.is_integer():
        raise ValueError(f"Column 'Resource' must be integer type, got {df['Resource'].dtype}")

    if df["Resource"].null_count() > 0:
        raise ValueError("Column 'Resource' cannot contain null values")

    if "Anchor" in df.columns and df["Anchor"].dtype not in (pl.Null, pl.String):
        raise ValueError(f"Column 'Anchor' must be String type, got {df['Anchor'].dtype}")


def _load_table(ref: IncludeDatasetRef) -> pl.DataFrame:
    format = ref.get_format()
    # TODO maybe this should be a generic function somewhere, it's duplicated with input specs probably!
    match format:
        case "csv":
            df = pl.read_csv(ref.local_path)
        case "tsv":
            df = pl.read_csv(ref.local_path, separator="\t")
        case "parquet":
            df = pl.read_parquet(ref.local_path)
        case _:
            assert_never(format)
    _validate_table_schema(df)
    return df


def _get_resource_row(resource: IncludeResourceRef, resource_mapping: dict[Path, int]) -> dict[str, int | str | None]:
    # TODO check if accessing store_entry_path like this is robust enough (see comment below)
    resource_id = resource_mapping[resource.store_entry_path]
    return {"Resource": resource_id, "Anchor": resource.anchor, **resource.metadata}


# TODO the resource mapping has some challenges if it's not a model regarding mis-use non-canonical paths,
#      e.g. they should never start with `/`  but this could also be validated in the originating model


def generate_output_table(config: BfabricOutputDataset, resource_mapping: dict[Path, int]) -> pl.DataFrame:
    """Generates the output table contents for the specified output dataset configuration.

    :param config: the output dataset configuration
    :param resource_mapping: a mapping of store_entry_path to resource_id of the resources which were created
    :return: the output table contents
    """
    # read the input tables
    tables_df = pl.concat([_load_table(ref) for ref in config.include_tables], how="diagonal_relaxed")

    # generate the rows for the resources
    resource_rows = []
    for resource in config.include_resources:
        resource_rows.append(_get_resource_row(resource, resource_mapping))
    resources_df = pl.from_dicts(resource_rows, strict=False)
    _validate_table_schema(resources_df)

    # concatenate these two dataframes now
    return pl.concat([tables_df, resources_df], how="diagonal_relaxed")
