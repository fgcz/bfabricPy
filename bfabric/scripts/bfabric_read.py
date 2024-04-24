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
    sys.stderr.write(f"\033[{color}m--- {msg} ---\033[0m\n")


def main():
    client = default_client()
    sys.stderr.write(bfabric.msg)

    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", help="endpoint to query", choices=bfabric.endpoints)
    parser.add_argument("attribute", help="attribute to query for", nargs="?")
    parser.add_argument("value", help="value to query for", nargs="?")
    args = parser.parse_args()

    query_obj = {}
    endpoint = args.endpoint
    attribute = args.attribute
    value = args.value
    if value is not None:
        query_obj[attribute] = value

    print_color_msg(f"query = {query_obj}")
    start_time = time.time()
    results = client.read(endpoint=endpoint, obj=query_obj)
    #results.sort("id")
    res = results.to_list_dict(drop_empty=False)
    res = sorted(res, key=lambda x: x["id"])
    possible_attributes = set(res[0].keys())
    end_time = time.time()

    try:
        # print json object
        if len(res) < 2:
            pprint(res[0], width=140)
    except Exception as e:
        # TODO fail more gracefully for no result case?
        print_color_msg(f"invalid query. {e}.", color=95)
        sys.exit(1)

    print_color_msg(f"possible attributes are: {possible_attributes}")

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
