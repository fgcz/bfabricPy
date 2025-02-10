#!/usr/bin/env python3
"""B-Fabric command line reader

Copyright:
    2014, 2019, 2024 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
    Christian Panse <cp@fgcz.ethz.ch>

License:
    GPL version 3

See also:
    http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import time
import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table

from bfabric import Bfabric, BfabricClientConfig
from bfabric.utils.cli_integration import use_client


def bfabric_read(
    client: Bfabric,
    endpoint: str,
    attribute: str | None,
    value: str | None,
    output_format: str,
) -> None:
    """Reads one or several items from a B-Fabric endpoint and prints them."""
    if attribute is not None and value is None:
        message = "value must be provided if attribute is provided"
        raise ValueError(message)

    query_obj = {attribute: value} if value is not None else {}

    logger.info(f"query = {query_obj}")
    console_out = Console()

    start_time = time.time()
    results = client.read(endpoint=endpoint, obj=query_obj)
    end_time = time.time()
    res = sorted(results.to_list_dict(drop_empty=False), key=lambda x: x["id"])
    if res:
        possible_attributes = sorted(set(res[0].keys()))
        logger.info(f"possible attributes = {possible_attributes}")

    output_format = _determine_output_format(console_out=console_out, output_format=output_format, n_results=len(res))
    logger.info(f"output format = {output_format}")

    if output_format == "json":
        print(json.dumps(res, indent=2))
    elif output_format == "yaml":
        print(yaml.dump(res))
    elif output_format == "table_tsv":
        _print_table_tsv(res)
    elif output_format == "table_rich":
        _print_table_rich(client.config, console_out, endpoint, res)
    else:
        raise ValueError(f"output format {output_format} not supported")

    logger.info(f"number of query result items = {len(res)}")
    logger.info(f"query time = {end_time - start_time:.2f} seconds")


def _print_table_rich(
    config: BfabricClientConfig,
    console_out: Console,
    endpoint: str,
    res: list[dict[str, Any]],
) -> None:
    """Prints the results as a rich table to the console."""
    table = Table("Id", "Created By", "Modified", "Name", "Grouping Var")
    for x in res:
        entry_url = f"{config.base_url}/{endpoint}/show.html?id={x['id']}"
        table.add_row(
            f"[link={entry_url}]{x['id']}[/link]",
            str(x["createdby"]),
            str(x["modified"]),
            x.get("name", ""),
            x.get("groupingvar", {}).get("name", "") or "",
        )
    console_out.print(table)


def _print_table_tsv(res: list[dict[str, Any]]) -> None:
    """Prints the results as a tab-separated table, using the original cols this script returned."""
    for x in res:
        print(
            "\t".join(
                [
                    str(x["id"]),
                    str(x["createdby"]),
                    str(x["modified"]),
                    x.get("name", ""),
                    x.get("groupingvar", {}).get("name") or "",
                ]
            )
        )


def _determine_output_format(console_out: Console, output_format: str, n_results: int) -> str:
    """Returns the format to use, based on the number of results, and whether the output is an interactive console.
    If the format is already set to a concrete value instead of "auto", it will be returned unchanged.
    """
    if output_format == "auto":
        if n_results < 2:
            output_format = "json"
        elif console_out.is_interactive:
            output_format = "table_rich"
        else:
            output_format = "table_tsv"
    return output_format


@use_client
def main(client: Bfabric) -> None:
    """Parses command line arguments and calls `bfabric_read`."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        help="output format",
        choices=["json", "yaml", "table_tsv", "table_rich", "auto"],
        default="auto",
        dest="output_format",
    )
    parser.add_argument("endpoint", help="endpoint to query", type=str)
    parser.add_argument("attribute", help="attribute to query for", nargs="?", type=str)
    parser.add_argument("value", help="value to query for", nargs="?")
    args = parser.parse_args()
    bfabric_read(client=client, **vars(args))


if __name__ == "__main__":
    main()
