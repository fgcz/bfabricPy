import json
import time
from enum import Enum
from typing import Any

import cyclopts
import yaml
from loguru import logger
from pydantic import BaseModel
from rich.console import Console
from rich.pretty import pprint
from rich.table import Table

from bfabric import Bfabric, BfabricClientConfig
from bfabric_scripts.cli.base import use_client


class OutputFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TABLE_RICH = "table_rich"
    AUTO = "auto"


app = cyclopts.App()


class CommandRead(BaseModel):
    format: OutputFormat
    limit: int
    query: dict[str, str]
    columns: list[str] | None
    max_columns: int


@app.default
@use_client
def bfabric_read(
    endpoint: str,
    attributes: list[tuple[str, str]] | None = None,
    *,
    client: Bfabric,
    output_format: OutputFormat = OutputFormat.AUTO,
    limit: int = 100,
    columns: list[str] | None = None,
    max_columns: int = 7,
) -> None:
    """Reads one or several items from a B-Fabric endpoint and prints them.

    Example usage:
    read workunit name "DIANN%" createdafter 2024-10-31T19:00:00

    :param endpoint: The endpoint to query.
    :param attributes: A list of attribute-value pairs to filter the results by.
    :param output_format: The output format to use.
    :param limit: The maximum number of results to return.
    :param columns: The columns to return (separate arguments).
    :param max_columns: The maximum number of columns to return (only relevant if no columns are passed explicitly and a table output is chosen).
    """
    console_out = Console()

    query = {attribute: value for attribute, value in attributes or []}
    results = _get_results(client=client, endpoint=endpoint, query=query, limit=limit)
    output_format = _determine_output_format(
        console_out=console_out, output_format=output_format, n_results=len(results)
    )
    output_columns = _determine_output_columns(
        results=results,
        columns=columns,
        max_columns=max_columns,
        output_format=output_format,
    )

    if output_format == OutputFormat.JSON:
        print(json.dumps(results, indent=2))
    elif output_format == OutputFormat.YAML:
        print(yaml.dump(results))
    elif output_format == OutputFormat.TABLE_RICH:
        pprint(
            CommandRead(
                format=output_format,
                limit=limit,
                query=query,
                columns=output_columns,
                max_columns=max_columns,
            ),
            console=console_out,
        )
        # _print_query_rich(console_out, query)
        _print_table_rich(
            client.config, console_out, endpoint, results, output_columns=output_columns
        )
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


def _get_results(
    client: Bfabric, endpoint: str, query: dict[str, str], limit: int
) -> list[dict[str, Any]]:
    start_time = time.time()
    results = client.read(endpoint=endpoint, obj=query, max_results=limit)
    end_time = time.time()
    logger.info(f"number of query result items = {len(results)}")
    logger.info(f"query time = {end_time - start_time:.2f} seconds")

    results = sorted(results.to_list_dict(drop_empty=False), key=lambda x: x["id"])
    if results:
        possible_attributes = sorted(set(results[0].keys()))
        logger.info(f"possible attributes = {possible_attributes}")

    return results


def _print_query_rich(
    console_out: Console,
    query: dict[str, str],
) -> None:
    pprint(query, console=console_out)


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


def _determine_output_format(
    console_out: Console, output_format: OutputFormat, n_results: int
) -> OutputFormat:
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
