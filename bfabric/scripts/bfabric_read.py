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
import argparse
import json
import time
from typing import Optional

from rich.console import Console
from rich.table import Table

import bfabric
from bfabric.bfabric2 import Bfabric, get_system_auth


def bfabric_read(endpoint: str, attribute: Optional[str], value: Optional[str], output_format: str) -> None:
    """Reads one or several items from a B-Fabric endpoint and prints them."""
    if attribute is not None and value is None:
        message = "value must be provided if attribute is provided"
        raise ValueError(message)

    client = Bfabric(*get_system_auth(), verbose=True)

    query_obj = {attribute: value} if value is not None else {}
    console_info = Console(style="bright_yellow", stderr=True)
    console_info.print(f"--- query = {query_obj} ---")
    console_out = Console()

    start_time = time.time()
    results = client.read(endpoint=endpoint, obj=query_obj)
    end_time = time.time()
    res = sorted(results.to_list_dict(drop_empty=False), key=lambda x: x["id"])

    if res:
        possible_attributes = sorted(set(res[0].keys()))
        console_info.print(f"--- possible attributes = {possible_attributes} ---")

    if output_format == "auto":
        if len(res) < 2:
            output_format = "json"
        elif console_out.is_interactive:
            output_format = "table_rich"
        else:
            output_format = "table_tsv"
    console_info.print(f"--- output format = {output_format} ---")

    if output_format == "json":
        print(json.dumps(res, indent=2))
    elif output_format == "table_tsv":
        for x in res:
            try:
                print(f'{x["id"]}\t{x["createdby"]}\t{x["modified"]}\t{x["name"]}\t{x["groupingvar"]["name"]}')
            except (KeyError, TypeError):
                print(f'{x["id"]}\t{x["createdby"]}\t{x["modified"]}')
    elif output_format == "table_rich":
        table = Table("id", "createdby", "modified", "name", "groupingvar")
        for x in res:
            entry_url = f"https://fgcz-bfabric.uzh.ch/bfabric/{endpoint}/show.html?id={x['id']}"
            table.add_row(
                f"[link={entry_url}]{x['id']}[/link]",
                str(x["createdby"]),
                str(x["modified"]),
                str(x["name"]),
                str(x.get("groupingvar")),
            )
        console_out.print(table)
    else:
        raise ValueError(f"output format {output_format} not supported")

    console_info.print(f"--- number of query result items = {len(res)} ---")
    console_info.print(f"--- query time = {end_time - start_time:.2f} seconds ---")


def main() -> None:
    """Parses command line arguments and calls `bfabric_read`."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        help="output format",
        choices=["json", "table_tsv", "table_rich", "auto"],
        default="auto",
        dest="output_format",
    )
    parser.add_argument("endpoint", help="endpoint to query", choices=bfabric.endpoints)
    parser.add_argument("attribute", help="attribute to query for", nargs="?")
    parser.add_argument("value", help="value to query for", nargs="?")
    args = parser.parse_args()
    bfabric_read(**vars(args))


if __name__ == "__main__":
    main()
