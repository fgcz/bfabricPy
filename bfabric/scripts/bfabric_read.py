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
import sys
import time
from typing import Optional

import bfabric
from bfabric.bfabric2 import default_client


def print_color_msg(msg, color="93"):
    print(f"\033[{color}m--- {msg} ---\033[0m", file=sys.stderr)


def bfabric_read(
    endpoint: str, attribute: Optional[str], value: Optional[str], output_format: str
):
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

    print_color_msg(f"number of query result items = {len(res)}")
    print_color_msg(f"query time = {round(end_time - start_time, 2)} seconds")


def main():
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
