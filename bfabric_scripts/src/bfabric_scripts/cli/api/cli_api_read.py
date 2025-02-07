import json
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Annotated

import cyclopts
import yaml
from bfabric import Bfabric, BfabricClientConfig
from bfabric_scripts.cli.base import use_client
from loguru import logger
from pydantic import BaseModel
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

app = cyclopts.App()


class OutputFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TABLE_RICH = "table_rich"
    TABLE_TSV = "table_tsv"


class Params(BaseModel):
    endpoint: str
    """Endpoint to query, e.g. 'resource'."""
    query: list[tuple[str, str]] = []
    """List of attribute-value pairs to filter the results by."""
    format: OutputFormat = OutputFormat.TABLE_RICH
    """Output format."""
    limit: int = 100
    """Maximum number of results."""
    columns: list[str] | None = None
    """Selection of columns to return."""
    cli_max_columns: int | None = 7
    """When showing the results as a table in the console (table-rich), the maximum number of columns to show."""

    file: Path | None = None
    """File to write the output to."""

    def extract_query(self) -> dict[str, str | list[str]]:
        """Returns the query as a dictionary which can be passed to the client."""
        query = defaultdict(list)
        for key, value in self.query:
            query[key].append(value)
        return {k: v[0] if len(v) == 1 else v for k, v in query.items()}


def perform_query(params: Params, client: Bfabric, console_user: Console) -> list[dict[str, Any]]:
    """Performs the query and returns the results."""
    query = params.extract_query()
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


def render_output(results: list[dict[str, Any]], params: Params, client: Bfabric, console: Console) -> str:
    """Renders the results in the specified output format."""
    if params.format == OutputFormat.JSON:
        return json.dumps(results, indent=2)
    elif params.format == OutputFormat.YAML:
        return yaml.dump(results)
    elif params.format == OutputFormat.TABLE_RICH:
        output_columns = _determine_output_columns(
            results=results,
            columns=params.columns,
            max_columns=params.cli_max_columns,
            output_format=params.format,
        )
        _print_table_rich(client.config, console, params.endpoint, results, output_columns=output_columns)
    else:
        raise ValueError(f"output format {params.format} not supported")


@app.default
@use_client
@logger.catch
def read(command: Annotated[Params, cyclopts.Parameter(name="*")], *, client: Bfabric) -> None:
    """Reads one type of entity from B-Fabric."""
    console_user = Console(stderr=True)
    console_user.print(command)

    # Perform the query
    results = perform_query(params=command, client=client, console_user=console_user)

    # Print/export output
    results = sorted(results, key=lambda x: x["id"])
    console_out = Console()
    output = render_output(results, params=command, client=client, console=console_out)
    if command.file:
        command.file.write_text(output)


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
