import json
from enum import Enum
from pathlib import Path
from typing import Any, Annotated

import cyclopts
import polars as pl
import pydantic
import yaml
from loguru import logger
from pydantic import BaseModel
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from bfabric import Bfabric, BfabricClientConfig
from bfabric.utils.cli_integration import use_client
from bfabric.utils.polars_utils import flatten_relations
from bfabric_scripts.cli.api.query_repr import Query


class OutputFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TSV = "tsv"
    TABLE_RICH = "table_rich"


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

    file: Path | None = None
    """File to write the output to."""

    @pydantic.field_validator("columns", mode="before")
    def convert_str_to_list(cls, value: list[str]) -> list[str]:
        return value[0].split(",") if (len(value) == 1 and "," in value[0]) else value


def perform_query(params: Params, client: Bfabric, console_user: Console) -> list[dict[str, Any]]:
    """Performs the query and returns the results."""
    query = params.query.to_dict(duplicates="collect")
    query_stmt = f"client.read(endpoint={params.endpoint!r}, obj={query!r}, max_results={params.limit!r})"
    results = eval(query_stmt)

    # Log query and results meta information
    python_code = (
        f"results = {query_stmt}\n"
        f"len(results) # {len(results)}\n"
        f"sorted(results.to_polars().columns) # {sorted(results.to_polars().columns)}"
    )
    console_user.print(
        Syntax(python_code, "python", theme="solarized-dark", background_color="default", word_wrap=True)
    )
    return results


def render_output(results: list[dict[str, Any]], params: Params, client: Bfabric, console: Console) -> str | None:
    """Renders the results in the specified output format."""
    if params.format == OutputFormat.TABLE_RICH:
        output_columns = _determine_output_columns(
            results=results,
            columns=params.columns,
            max_columns=params.cli_max_columns,
            output_format=params.format,
        )
        _print_table_rich(client.config, console, params.endpoint, results, output_columns=output_columns)
        return None
    else:
        if params.columns:
            results = [{k: x.get(k) for k in params.columns} for x in results]

        if params.format == OutputFormat.JSON:
            result = json.dumps(results, indent=2)
        elif params.format == OutputFormat.YAML:
            result = yaml.dump(results)
        elif params.format == OutputFormat.TSV:
            result = flatten_relations(pl.DataFrame(results)).write_csv(separator="\t")
        else:
            raise ValueError(f"output format {params.format} not supported")

        # TODO check if we can add back colors (but it broke some stuff, because of forced line breaks, so be careful)
        print(result)
        return result


@use_client
@logger.catch(reraise=True)
def cmd_api_read(params: Annotated[Params, cyclopts.Parameter(name="*")], *, client: Bfabric) -> None | int:
    """Reads entities from B-Fabric."""
    console_user = Console(stderr=True)
    console_user.print(params)

    # Perform the query
    results = perform_query(params=params, client=client, console_user=console_user)

    # Print/export output
    results = sorted(results, key=lambda x: x["id"])
    console_out = Console()
    output = render_output(results, params=params, client=client, console=console_out)
    if params.file:
        if output is None:
            logger.error("File output is not supported for the specified output format.")
            return 1
        params.file.write_text(output)
        logger.info(f"Results written to {params.file} (size: {params.file.stat().st_size} bytes)")


def _determine_output_columns(
    results: list[dict[str, Any]],
    columns: list[str] | None,
    max_columns: int,
    output_format: OutputFormat,
) -> list[str]:
    if not columns:
        if max_columns < 1:
            raise ValueError("max_columns must be at least 1")
        columns = ["id"]
        available_columns = sorted(set(results[0].keys()) - {"id"})
        columns += available_columns[:max_columns]

    return columns


def _print_table_rich(
    config: BfabricClientConfig,
    console_out: Console,
    endpoint: str,
    res: list[dict[str, Any]],
    output_columns: list[str],
) -> None:
    """Prints the results as a rich table to the console."""
    table = Table(*output_columns)
    for x in res:
        entry_url = f"{config.base_url}/{endpoint}/show.html?id={x['id']}"
        values = []
        for column in output_columns:
            if column == "id":
                values.append(f"[link={entry_url}]{x['id']}[/link]")
            elif column == "groupingvar":
                values.append(x.get(column, {}).get("name", "") or "")
            elif isinstance(x.get(column), dict):
                values.append(str(x.get(column, {}).get("id", "")))
            else:
                values.append(str(x.get(column, "")))
        table.add_row(*values)
    console_out.print(table)
