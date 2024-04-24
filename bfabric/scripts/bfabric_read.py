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
import sys
import time
import bfabric
from pprint import pprint
from bfabric.bfabric2 import default_client, BfabricAPIEngineType


def print_color_msg(msg, color="93"):
    print(f"\033[{color}m--- {msg} ---\033[0m", file=sys.stderr)


def main():
    client = default_client()
    sys.stderr.write(bfabric.msg)

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", help="output mode", choices=["json", "table", "auto"], default="auto")
    parser.add_argument("endpoint", help="endpoint to query", choices=bfabric.endpoints)
    parser.add_argument("attribute", help="attribute to query for", nargs="?")
    parser.add_argument("value", help="value to query for", nargs="?")
    args = parser.parse_args()

    query_obj = {}
    endpoint = args.endpoint
    attribute = args.attribute
    value = args.value
    output_mode = args.mode
    if value is not None:
        query_obj[attribute] = value

    print_color_msg(f"query = {query_obj}")
    start_time = time.time()
    results = client.read(endpoint=endpoint, obj=query_obj)
    end_time = time.time()
    res = results.to_list_dict(drop_empty=False)
    res = sorted(res, key=lambda x: x["id"])

    if res:
        possible_attributes = set(res[0].keys())
        print_color_msg(f"possible attributes are: {possible_attributes}")

    if output_mode == "auto":
        output_mode = "json" if len(res) < 2 else "table"

    if output_mode == "json":
        pprint(res, width=140)
    elif output_mode == "table":
        for x in res:
            try:
                print(
                    f'{x["id"]}\t{x["createdby"]}\t{x["modified"]}\t{x["name"]}\t{x["groupingvar"]["name"]}'
                )
            except (KeyError, TypeError):
                print(f'{x["id"]}\t{x["createdby"]}\t{x["modified"]}')

    print_color_msg(f"number of query result items = {len(res)}")
    print_color_msg(f"query time = {round(end_time - start_time, 2)} seconds")


if __name__ == "__main__":
    main()
