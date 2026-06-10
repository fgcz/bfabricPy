import json
from enum import Enum

import polars as pl
import yaml
from rich.console import Console
from rich.table import Table

from bfabric import Bfabric, BfabricClientConfig
from bfabric.typing import ApiResponseObjectType
from bfabric.utils.polars_utils import flatten_relations


class OutputFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TSV = "tsv"
    TABLE_RICH = "table_rich"


def render_output(
    results: list[ApiResponseObjectType],
    *,
    output_format: OutputFormat,
    endpoint: str,
    client: Bfabric,
    console: Console,
    columns: list[str] | None = None,
    max_columns: int | None = 7,
) -> str | None:
    """Renders *results* in the requested format.

    Returns the rendered string (for JSON/YAML/TSV) or None (for TABLE_RICH, which writes
    directly to *console*).
    """
    if output_format == OutputFormat.TABLE_RICH:
        output_columns = _determine_output_columns(
            results=results,
            columns=columns,
            max_columns=max_columns,
        )
        _print_table_rich(client.config, console, endpoint, results, output_columns=output_columns)
        return None

    if columns:
        results = [{k: x.get(k) for k in columns} for x in results]

    if output_format == OutputFormat.JSON:
        # default=str makes the output engine-agnostic: the Zeep engine can return
        # datetime/Decimal objects that are not natively JSON-serialisable.
        result = json.dumps(results, indent=2, default=str)
    elif output_format == OutputFormat.YAML:
        result = yaml.dump(results)
    elif output_format == OutputFormat.TSV:
        result = flatten_relations(pl.DataFrame(results)).write_csv(separator="\t")
    else:
        raise ValueError(f"output format {output_format} not supported")  # pyright: ignore[reportUnreachable]

    print(result)
    return result


def _determine_output_columns(
    results: list[ApiResponseObjectType],
    columns: list[str] | None,
    max_columns: int | None,
) -> list[str]:
    if not columns:
        if max_columns is not None and max_columns < 1:
            raise ValueError("max_columns must be at least 1")
        columns = ["id"]
        if not results:
            return columns
        available_columns = sorted(set(results[0].keys()) - {"id"})
        if max_columns is None:
            columns += available_columns
        else:
            columns += available_columns[:max_columns]
    return columns


def _print_table_rich(
    config: BfabricClientConfig,
    console_out: Console,
    endpoint: str,
    res: list[ApiResponseObjectType],
    output_columns: list[str],
) -> None:
    """Prints the results as a rich table to the console."""
    table = Table(*output_columns)
    for x in res:
        entry_url = f"{config.base_url}/{endpoint}/show.html?id={x['id']}"
        values: list[str] = []
        for column in output_columns:
            if column == "id":
                values.append(f"[link={entry_url}]{x['id']}[/link]")
            elif column == "groupingvar":
                val = x.get(column)
                values.append(str(val.get("name", "")) if isinstance(val, dict) else "")
            elif isinstance(val := x.get(column), dict):
                values.append(str(val.get("id", "")))
            else:
                values.append(str(x.get(column, "")))
        table.add_row(*values)
    console_out.print(table)
