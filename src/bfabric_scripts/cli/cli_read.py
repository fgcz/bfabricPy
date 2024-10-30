from __future__ import annotations

import json
import time
from enum import Enum
from typing import Any

import cyclopts
import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table

from bfabric import Bfabric, BfabricClientConfig
from bfabric.cli_formatting import setup_script_logging


class OutputFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TABLE_RICH = "table_rich"
    AUTO = "auto"


app = cyclopts.App()


@app.default
def bfabric_read(
    endpoint: str,
    attribute: str | None = None,
    value: str | None = None,
    *,
    output_format: OutputFormat = OutputFormat.AUTO,
    limit: int = 100,
    columns: list[str] | None = None,
    max_columns: int = 7,
) -> None:
    """Reads one or several items from a B-Fabric endpoint and prints them.

    :param endpoint: The endpoint to query.
    :param attribute: The attribute to query for.
    :param value: The value to query for.
    :param output_format: The output format to use.
    :param limit: The maximum number of results to return.
    :param columns: The columns to return (separate arguments).
    :param max_columns: The maximum number of columns to return (only relevant if no columns are passed explicitly and a table output is chosen).
    """
    setup_script_logging()
    client = Bfabric.from_config()
    console_out = Console()

    results = _get_results(client=client, endpoint=endpoint, attribute=attribute, value=value, limit=limit)
    output_format = _determine_output_format(
        console_out=console_out, output_format=output_format, n_results=len(results)
    )
    output_columns = _determine_output_columns(
        results=results, columns=columns, max_columns=max_columns, output_format=output_format
    )

    if output_format == OutputFormat.JSON:
        print(json.dumps(results, indent=2))
    elif output_format == OutputFormat.YAML:
        print(yaml.dump(results))
    elif output_format == OutputFormat.TABLE_RICH:
        _print_table_rich(client.config, console_out, endpoint, results, output_columns=output_columns)
    else:
        raise ValueError(f"output format {output_format} not supported")


def _determine_output_columns(
    results: list[dict[str, Any]], columns: list[str] | None, max_columns: int, output_format: OutputFormat
) -> list[str]:
    if not columns:
        if max_columns < 1:
            raise ValueError("max_columns must be at least 1")
        columns = ["id"]
        available_columns = sorted(set(results[0].keys()) - {"id"})
        columns += available_columns[:max_columns]

    logger.info(f"columns = {columns}")
    return columns


def _get_results(client: Bfabric, endpoint: str, attribute: str, value: str, limit: int) -> list[dict[str, Any]]:
    if attribute is not None and value is None:
        message = "value must be provided if attribute is provided"
        raise ValueError(message)
    start_time = time.time()
    results = client.read(endpoint=endpoint, obj={attribute: value} if value is not None else {}, max_results=limit)
    end_time = time.time()
    logger.info(f"number of query result items = {len(results)}")
    logger.info(f"query time = {end_time - start_time:.2f} seconds")

    results = sorted(results.to_list_dict(drop_empty=False), key=lambda x: x["id"])
    if results:
        possible_attributes = sorted(set(results[0].keys()))
        logger.info(f"possible attributes = {possible_attributes}")

    return results


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
            output_format = OutputFormat.JSON
        elif console_out.is_interactive:
            output_format = OutputFormat.TABLE_RICH
        else:
            output_format = OutputFormat.TABLE_TSV
    logger.info(f"output format = {output_format}")
    return output_format
