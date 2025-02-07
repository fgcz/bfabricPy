import json
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Annotated

import cyclopts
import rich.pretty
import yaml
from bfabric import Bfabric, BfabricClientConfig
from bfabric_scripts.cli.base import use_client
from loguru import logger
from pydantic import BaseModel
from rich.console import Console
from rich.pretty import pprint
from rich.syntax import Syntax
from rich.table import Table

app = cyclopts.App()


class OutputFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TABLE_RICH = "table_rich"
    TABLE_TSV = "table_tsv"
    AUTO = "auto"


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
    max_columns: int | None = None
    # TODO max columns is problematic

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
    rich.pretty.pprint(command)

    query = command.extract_query()
    query_stmt = f"client.read(endpoint={command.endpoint!r}, obj={query!r}, max_results={command.limit!r})"
    results = eval(query_stmt)

    console_out = Console()
    python_code = (
        f"results = {query_stmt}\n"
        f"len(results) # {len(results)}\n"
        f"sorted(results.to_polars().columns) # {sorted(results.to_polars().columns)}"
    )
    results = sorted(results, key=lambda x: x["id"])
    console_out.print(Syntax(python_code, "python", theme="solarized-dark", background_color="default", word_wrap=True))
    output_format = _determine_output_format(
        console_out=console_out, output_format=command.format, n_results=len(results)
    )

    if output_format == OutputFormat.JSON:
        print(json.dumps(results, indent=2))
    elif output_format == OutputFormat.YAML:
        print(yaml.dump(results))
    elif output_format == OutputFormat.TABLE_RICH:
        output_columns = _determine_output_columns(
            results=results,
            columns=columns,
            max_columns=max_columns,
            output_format=output_format,
        )
        pprint(
            Params(
                format=output_format,
                limit=limit,
                query=query,
                columns=output_columns,
                max_columns=max_columns,
            ),
            console=console_out,
        )
        # _print_query_rich(console_out, query)
        _print_table_rich(client.config, console_out, endpoint, results, output_columns=output_columns)
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

    logger.info(f"columns = {columns}")
    return columns


# def _get_results(client: Bfabric, endpoint: str, query: dict[str, str], limit: int) -> list[dict[str, Any]]:
#    # TODO move timing into the client
#    #start_time = time.time()
#    results = client.read(endpoint=endpoint, obj=query, max_results=limit)
#    #end_time = time.time()
#    #logger.debug(f"query time = {end_time - start_time:.2f} seconds")
#
#    results = sorted(results.to_list_dict(drop_empty=False), key=lambda x: x["id"])
#    if results:
#        possible_attributes = sorted(set(results[0].keys()))
#        logger.info(f"possible attributes = {possible_attributes}")
#
#    return results


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


def _determine_output_format(console_out: Console, output_format: OutputFormat, n_results: int) -> OutputFormat:
    """Returns the format to use, based on the number of results, and whether the output is an interactive console.
    If the format is already set to a concrete value instead of "auto", it will be returned unchanged.
    """
    if output_format == OutputFormat.AUTO:
        if n_results < 2:
            output_format = OutputFormat.YAML
        else:
            output_format = OutputFormat.TABLE_RICH
    logger.info(f"output format = {output_format}")
    return output_format
