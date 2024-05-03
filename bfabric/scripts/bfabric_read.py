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

import bfabric
from bfabric.bfabric2 import Bfabric, get_system_auth


def bfabric_read(
    endpoint: str, attribute: Optional[str], value: Optional[str], output_format: str
) -> None:
    """Reads one or several items from a B-Fabric endpoint and prints them."""
    if attribute is not None and value is None:
        message = "value must be provided if attribute is provided"
        raise ValueError(message)

    client = Bfabric(*get_system_auth(), verbose=True)

    query_obj = {attribute: value} if value is not None else {}
    console = Console(style="bright_yellow", stderr=True)
    console.print(f"--- query = {query_obj} ---")

    start_time = time.time()
    results = client.read(endpoint=endpoint, obj=query_obj)
    end_time = time.time()
    res = sorted(results.to_list_dict(drop_empty=False), key=lambda x: x["id"])

    if res:
        possible_attributes = sorted(set(res[0].keys()))
        console.print(f"--- possible attributes = {possible_attributes} ---")

    if output_format == "auto":
        output_format = "json" if len(res) < 2 else "table_tsv"

    if output_format == "json":
        print(json.dumps(res, indent=2))
    elif output_format == "table_tsv":
        for x in res:
            try:
                print(
                    f'{x["id"]}\t{x["createdby"]}\t{x["modified"]}\t{x["name"]}\t{x["groupingvar"]["name"]}'
                )
            except (KeyError, TypeError):
                print(f'{x["id"]}\t{x["createdby"]}\t{x["modified"]}')

    console.print(f"--- number of query result items = {len(res)} ---")
    console.print(f"--- query time = {end_time - start_time:.2f} seconds ---")


def main() -> None:
    """Parses command line arguments and calls `bfabric_read`."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        help="output format",
        choices=["json", "table_tsv", "auto"],
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
