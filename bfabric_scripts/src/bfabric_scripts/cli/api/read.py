from pathlib import Path
from typing import Annotated, cast

import cyclopts
import pydantic
from loguru import logger
from pydantic import BaseModel
from rich.console import Console

from bfabric import Bfabric
from bfabric.typing import ApiResponseObjectType
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.cli.api.output_format import OutputFormat, render_output
from bfabric_scripts.cli.api.query_repr import Query

# Re-export so that existing callers (e.g. tests) can still do:
#   from bfabric_scripts.cli.api.read import OutputFormat, render_output
__all__ = ["OutputFormat", "render_output"]


class Params(BaseModel):
    endpoint: str
    """Endpoint to query, e.g. 'resource'."""
    query: Query = Query()
    """List of attribute-value pairs to filter the results by."""
    format: OutputFormat = OutputFormat.TABLE_RICH
    """Output format."""
    limit: int = 100
    """Maximum number of results."""
    columns: list[str] = []
    """Selection of columns to return, comma separated list."""
    cli_max_columns: int | None = 7
    """When showing the results as a table in the console (table-rich), the maximum number of columns to show."""
    return_id_only: bool = False
    """If True, only returns entity IDs instead of full data (faster)."""

    file: Path | None = None
    """File to write the output to."""

    @pydantic.field_validator("columns", mode="before")
    def convert_str_to_list(cls, value: list[str]) -> list[str]:
        return value[0].split(",") if (len(value) == 1 and "," in value[0]) else value


def perform_query(params: Params, client: Bfabric) -> list[ApiResponseObjectType]:
    """Performs the query and returns the results."""
    query = params.query.to_dict(duplicates="collect")
    query_stmt = f"client.read(endpoint={params.endpoint!r}, obj={query!r}, max_results={params.limit!r}, return_id_only={params.return_id_only!r})"
    results = eval(query_stmt)

    # Log query and results meta information
    python_code = (
        f"results = {query_stmt}\n"
        f"len(results) # {len(results)}\n"
        f"sorted(results.to_polars().columns) # {sorted(results.to_polars().columns)}"
    )
    logger.info("\n{}", python_code)
    return results


@use_client
def cmd_api_read(params: Annotated[Params, cyclopts.Parameter(name="*")], *, client: Bfabric) -> None | int:
    """Reads entities from B-Fabric."""
    logger.info("{}", params)

    # Perform the query
    results = perform_query(params=params, client=client)

    # Handle empty results gracefully for table format
    if not results:
        if params.format == OutputFormat.TABLE_RICH:
            logger.info("No results found for the given query.")
            return None
        # For other formats (JSON, YAML, TSV), continue to render empty results

    # Print/export output
    results = sorted(results, key=lambda x: cast(int, x["id"]))
    console_out = Console()
    output = render_output(
        results,
        output_format=params.format,
        endpoint=params.endpoint,
        client=client,
        console=console_out,
        columns=params.columns or None,
        max_columns=params.cli_max_columns,
    )
    if params.file:
        if output is None:
            logger.error("File output is not supported for the specified output format.")
            return 1
        params.file.write_text(output)
        logger.info(f"Results written to {params.file} (size: {params.file.stat().st_size} bytes)")
