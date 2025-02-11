from pathlib import Path
from typing import Literal, Annotated

import cyclopts
from pydantic import BaseModel, Field

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client


class InputFormatParquet(BaseModel):
    format: Literal["parquet"] = "parquet"


class InputFormatCsv(BaseModel):
    format: Literal["csv"] = "csv"
    has_header: bool = True


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
    # TODO this does not work like this
    format: Annotated[InputFormatParquet | InputFormatCsv, cyclopts.Parameter(name="*")] = Field(discriminator="format")


@use_client
def upload_dataset(params: Params, *, client: Bfabric) -> None:
    # TODO this is a bit more complex:
    #  - parquet: straightforward, just import the data, maybe check for invalid characters too
    #  - csv: we need "has_header"/"skip_lines", "separator"
    pass
