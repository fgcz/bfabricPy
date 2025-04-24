#!/usr/bin/env python3
"""
Copyright (C) 2022 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3


2022-06-03 add sample.name

Usage example:
  bfabric_read_samples_of_workunit.py 278175
"""

import argparse
import time

from rich.console import Console

from bfabric import Bfabric


def bfabric_read_samples_of_workunit(workunit_id: int) -> None:
    """Reads the samples of the specified workunit and prints the results to stdout."""
    client = Bfabric.connect()

    start_time = time.time()
    res_workunit = client.read(endpoint="workunit", obj={"id": workunit_id}).to_list_dict()[0]
    input_resource_ids = [x["id"] for x in res_workunit.get("inputresource", [])]
    input_resources = client.read(endpoint="resource", obj={"id": input_resource_ids}).to_list_dict()
    input_resources_name = [(r["id"], r["name"]) for r in input_resources]

    samples = client.read(endpoint="sample", obj={"id": [x["sample"]["id"] for x in input_resources]}).to_list_dict()
    groupingvars = [(s["id"], s["name"], (s.get("groupingvar") or {}).get("name", "NA")) for s in samples]

    print(
        "\t".join(
            [
                "workunit_id",
                "inputresource_id",
                "inputresource_name",
                "sample_name",
                "groupingvar_name",
            ]
        )
    )
    for i in zip(input_resources_name, groupingvars):
        print("\t".join([str(workunit_id), str(i[0][0]), i[0][1], i[1][1], i[1][2]]))

    end_time = time.time()
    Console(stderr=True).print(
        f"--- query time = {end_time - start_time:.2f} seconds ---",
        style="bright_yellow",
    )


def main() -> None:
    """Parses the command line arguments and calls `bfabric_read_samples_of_workunit`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("workunit_id", type=int, help="workunit id")
    args = parser.parse_args()
    bfabric_read_samples_of_workunit(workunit_id=args.workunit_id)


if __name__ == "__main__":
    # main()
    bfabric_read_samples_of_workunit(285689)
