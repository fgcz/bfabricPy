from enum import Enum
from pathlib import Path

import cyclopts
import sys
from loguru import logger
from pydantic import BaseModel

from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.optional_features import is_excel_available


class OutputFormat(Enum):
    AUTO = "auto"
    CSV = "csv"
    TSV = "tsv"
    PARQUET = "parquet"
    EXCEL = "excel"


def _infer_format_from_path(path: Path) -> OutputFormat:
    """Infers the output format from the file extension."""
    extension_map = {
        ".csv": OutputFormat.CSV,
        ".tsv": OutputFormat.TSV,
        ".parquet": OutputFormat.PARQUET,
        ".xlsx": OutputFormat.EXCEL,
    }

    suffix = path.suffix.lower()
    if suffix not in extension_map:
        msg = f"Cannot infer format from file extension '{suffix}'. Please specify --format explicitly."
        raise ValueError(msg)

    return extension_map[suffix]


@cyclopts.Parameter(name="*")
class Params(BaseModel):
    dataset_id: int
    """The dataset ID to download."""
    file: Path
    """The file to download the dataset to."""
    format: OutputFormat = OutputFormat.AUTO
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

    # Infer format if AUTO
    output_format = params.format
    if output_format == OutputFormat.AUTO:
        output_format = _infer_format_from_path(params.file)

    # Check Excel availability
    if output_format == OutputFormat.EXCEL and not is_excel_available():
        msg = (
            "Excel format requires the 'excel' optional dependency. Install with: pip install 'bfabric_scripts[excel]'"
        )
        raise RuntimeError(msg)

    # Write the result
    with logger.catch(onerror=lambda _: sys.exit(1)):
        match output_format:
            case OutputFormat.CSV | OutputFormat.TSV:
                dataset.write_csv(params.file, separator="\t" if output_format == OutputFormat.TSV else ",")
            case OutputFormat.PARQUET:
                dataset.to_polars().write_parquet(params.file)
            case OutputFormat.EXCEL:
                dataset.to_polars().write_excel(params.file)
    logger.info(f"Result written to {params.file} ({params.file.stat().st_size / 1024:.2f} KB)")
