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


@app.default
@use_client
@logger.catch
def read(command: Annotated[Params, cyclopts.Parameter(name="*")], *, client: Bfabric) -> None:
    """Reads one type of entity from B-Fabric."""
    console_user = Console(stderr=True)
    console_user.print(command)

    # Perform query
    query = command.extract_query()
    query_stmt = f"client.read(endpoint={command.endpoint!r}, obj={query!r}, max_results={command.limit!r})"
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

    # Print/export output
    results = sorted(results, key=lambda x: x["id"])
    output_format = command.format

    if output_format == OutputFormat.JSON:
        print(json.dumps(results, indent=2))
    elif output_format == OutputFormat.YAML:
        print(yaml.dump(results))
    elif output_format == OutputFormat.TABLE_RICH:
        output_columns = _determine_output_columns(
            results=results,
            columns=command.columns,
            max_columns=command.cli_max_columns,
            output_format=output_format,
        )
        _print_table_rich(client.config, console_user, command.endpoint, results, output_columns=output_columns)
    else:
        raise ValueError(f"output format {output_format} not supported")


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
