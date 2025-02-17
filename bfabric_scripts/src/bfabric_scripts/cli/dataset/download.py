from enum import Enum
from pathlib import Path

import cyclopts
import sys
from loguru import logger
from pydantic import BaseModel

from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.utils.cli_integration import use_client


class OutputFormat(Enum):
    CSV = "csv"
    TSV = "tsv"
    PARQUET = "parquet"


@cyclopts.Parameter(name="*")
class Params(BaseModel):
    dataset_id: int
    """The dataset ID to download."""
    file: Path
    """The file to download the dataset to."""
    format: OutputFormat = OutputFormat.CSV
    """The format to download the dataset in."""


@use_client
def cmd_dataset_download(params: Params, *, client: Bfabric) -> None:
    """Download a dataset from B-Fabric."""
    # Find the dataset
    dataset = Dataset.find(id=params.dataset_id, client=client)
    if not dataset:
        msg = f"Dataset with id {params.dataset_id!r} not found."
        raise ValueError(msg)

    # Create the output directory if it does not exist
    params.file.parent.mkdir(parents=True, exist_ok=True)

    # Write the result
    with logger.catch(onerror=lambda _: sys.exit(1)):
        match params.format:
            case OutputFormat.CSV | OutputFormat.TSV:
                dataset.write_csv(params.file, separator="\t" if params.format == OutputFormat.TSV else ",")
            case OutputFormat.PARQUET:
                dataset.to_polars().write_parquet(params.file)
    logger.info(f"Result written to {params.file} ({params.file.stat().st_size / 1024:.2f} KB)")
