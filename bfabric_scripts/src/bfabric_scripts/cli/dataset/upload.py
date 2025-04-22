from enum import Enum
from pathlib import Path

import cyclopts
import polars as pl
from loguru import logger
from pydantic import BaseModel, model_validator

from bfabric import Bfabric
from bfabric.experimental.upload_dataset import (
    check_for_invalid_characters,
    polars_to_bfabric_dataset,
    warn_on_trailing_spaces,
)
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.optional_features import decorate_if_excel


class InputFormat(Enum):
    CSV = "csv"
    PARQUET = "parquet"


@cyclopts.Parameter(name="*")
class Params(BaseModel):
    file: Path
    """The file to upload."""
    container_id: int
    """The container ID to upload the dataset to."""
    dataset_name: str | None = None
    """If set, the dataset will be given this name, otherwise it will default to the file name without the extension."""
    workunit_id: int | None = None
    """Register the dataset to have been created-by a workunit."""
    forbidden_chars: str | None = ",\t"
    """Characters which are not permitted in a cell (set to empty string to deactivate)."""
    warn_trailing_spaces: bool = True
    """Whether to warn about trailing whitespace in the dataset."""


@cyclopts.Parameter(name="*")
class CsvParams(Params):
    has_header: bool = True
    """Whether the input file has a header."""
    separator: str | None = None
    """The separator to use in the CSV file."""


@cyclopts.Parameter(name="*")
class XlsxParams(Params):
    sheet_id: int | None = None
    """Index of the sheet to read (first sheet is 1)."""
    sheet_name: str | None = None
    """Name of the sheet to read."""

    @model_validator(mode="after")
    def either_sheet_id_or_name_or_neither(self):
        if self.sheet_id is None and self.sheet_name is None:
            # This is the default behavior, so we don't need to do anything
            return self
        if self.sheet_id is not None and self.sheet_name is not None:
            raise ValueError("You can only specify one of sheet_id or sheet_name.")
        if self.sheet_id is not None and self.sheet_id < 1:
            raise ValueError("sheet_id must be greater than or equal to 1.")
        if self.sheet_name is not None and self.sheet_name == "":
            raise ValueError("sheet_name must not be empty.")
        return self


cmd_dataset_upload = cyclopts.App(help="Upload a dataset to B-Fabric.")


@cmd_dataset_upload.command
@use_client
def csv(params: CsvParams, *, client: Bfabric) -> None:
    """Upload a CSV file as a B-Fabric dataset."""
    params.separator = "," if params.separator is None else params.separator
    table = pl.read_csv(params.file, separator=params.separator, has_header=params.has_header)
    upload_table(table=table, params=params, client=client)


@cmd_dataset_upload.command
@use_client
def tsv(params: CsvParams, *, client: Bfabric) -> None:
    """Upload a TSV file as a B-Fabric dataset."""
    params.separator = "\t" if params.separator is None else params.separator
    # Defer to the CSV command
    csv(params, client=client)


@decorate_if_excel(cmd_dataset_upload.command)
@use_client
def xlsx(params: XlsxParams, *, client: Bfabric) -> None:
    """Upload an Excel file as a B-Fabric dataset.

    You can specify the sheet to read, but by default sheet 1 will be read automatically.
    """
    table = pl.read_excel(params.file, sheet_id=params.sheet_id, sheet_name=params.sheet_name)
    upload_table(table=table, params=params, client=client)


@cmd_dataset_upload.command
@use_client
def parquet(params: Params, *, client: Bfabric) -> None:
    """Upload a Parquet file as a B-Fabric dataset."""
    table = pl.read_parquet(params.file)
    upload_table(table=table, params=params, client=client)


def upload_table(table: pl.DataFrame, params: Params, client: Bfabric) -> None:
    if params.forbidden_chars:
        check_for_invalid_characters(data=table, invalid_characters=params.forbidden_chars)

    if params.warn_trailing_spaces:
        warn_on_trailing_spaces(table)

    obj = polars_to_bfabric_dataset(table)
    obj["name"] = params.dataset_name or params.file.stem
    obj["containerid"] = params.container_id
    if params.workunit_id is not None:
        obj["workunitid"] = params.workunit_id
    endpoint = "dataset"
    res = client.save(endpoint=endpoint, obj=obj)
    logger.success(
        f"Dataset {res[0]['id']} with name {res[0]['name']} in container {res[0]['container']['id']}"
        f" has been created successfully."
    )
