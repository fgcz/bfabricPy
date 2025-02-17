from enum import Enum
from pathlib import Path
from typing import Self
import polars as pl
import cyclopts
from pydantic import BaseModel, model_validator
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client


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

    format: InputFormat = InputFormat.CSV
    """The format of the input file."""
    has_header: bool = True
    """Whether the input file has a header (not relevant for Parquet)."""
    separator: str = ","
    """The separator to use in the CSV file (not relevant for Parquet)."""
    forbidden_chars: str = ",\t"
    """Characters which are not permitted in a cell (set to empty string to deactivate)."""

    @model_validator(mode="after")
    def ensure_no_weird_parquet_options(self) -> Self:
        if self.format != InputFormat.PARQUET:
            return self
        if self.has_header:
            raise ValueError("Parquet files do not support has_header (as it makes no sense)")


def read_data(params: Params) -> pl.DataFrame:
    if params.format == InputFormat.CSV:
        return pl.read_csv(params.file, separator=, has_header=params.has_header)



cmd_dataset_upload = cyclopts.App(help="upload a dataset to B-Fabric")

# TODO subcommands: csv, tsv, parquet (but csv and tvs are the same iwth a different default separator, tho both should allow to customize it)


@use_client
def cmd_dataset_upload(params: Params, *, client: Bfabric) -> None:
    # TODO this is a bit more complex:
    #  - parquet: straightforward, just import the data, maybe check for invalid characters too
    #  - csv: we need "has_header"/"skip_lines", "separator"
    pprint(params)
