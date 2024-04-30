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
import enum
import json
import sys
import time
from typing import Optional, Annotated

import typer

import bfabric
from bfabric.bfabric2 import default_client


def print_color_msg(msg, color="93"):
    print(f"\033[{color}m--- {msg} ---\033[0m", file=sys.stderr)


class OutputFormat(enum.Enum):
    auto = "auto"
    json = "json"
    table_tsv = "table_tsv"


def bfabric_read(
    endpoint: str,
    attribute: Annotated[Optional[str], typer.Argument()] = None,
    value: Annotated[Optional[str], typer.Argument()] = None,
    format: OutputFormat = "auto",
):
    if endpoint not in bfabric.endpoints:
        raise ValueError(f"endpoint: invalid choice {endpoint}")

    query_obj = {attribute: value} if value is not None else {}
    print_color_msg(f"query = {query_obj}")

    client = default_client()
    sys.stderr.write(bfabric.msg)
    start_time = time.time()
    results = client.read(endpoint=endpoint, obj=query_obj)
    end_time = time.time()
    res = sorted(results.to_list_dict(drop_empty=False), key=lambda x: x["id"])

    if res:
        possible_attributes = set(res[0].keys())
        print_color_msg(f"possible attributes are: {possible_attributes}")

    if format == OutputFormat.auto:
        format = OutputFormat.json if len(res) < 2 else OutputFormat.table_tsv

    if format == OutputFormat.json:
        print(json.dumps(res, indent=2))
    elif format == OutputFormat.table_tsv:
        for x in res:
            try:
                print(
                    f'{x["id"]}\t{x["createdby"]}\t{x["modified"]}\t{x["name"]}\t{x["groupingvar"]["name"]}'
                )
            except (KeyError, TypeError):
                print(f'{x["id"]}\t{x["createdby"]}\t{x["modified"]}')
    else:
        raise ValueError(f"unknown output format {format}")

    print_color_msg(f"number of query result items = {len(res)}")
    print_color_msg(f"query time = {round(end_time - start_time, 2)} seconds")


def main():
    typer.run(bfabric_read)


if __name__ == "__main__":
    main()
