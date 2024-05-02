#!/usr/bin/env python3
# -*- coding: latin1 -*-

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
import sys
import time

import bfabric
from bfabric.bfabric2 import Bfabric, get_system_auth


def print_color_msg(msg, color="93"):
    msg = "\033[{color}m--- {} ---\033[0m\n".format(msg, color=color)
    sys.stderr.write(msg)


def bfabric_read_samples_of_workunit(workunit_id: int):
    client = Bfabric(*get_system_auth())
    sys.stderr.write(bfabric.msg)

    start_time = time.time()
    res_workunit = client.read(endpoint="workunit", obj={"id": workunit_id}).to_list_dict()[0]
    input_resource_ids = [x["id"] for x in res_workunit.get("inputresource", [])]
    input_resources = client.read(endpoint="resource", obj={"id": input_resource_ids}).to_list_dict()
    input_resources_name = [(r["id"], r["name"]) for r in input_resources]

    samples = client.read(endpoint="sample", obj={"id": [x["sample"]["id"] for x in input_resources]}).to_list_dict()
    groupingvars = [(s["id"], s["name"], (s.get("groupingvar") or {}).get("name", "NA")) for s in samples]

    print("\t".join(["workunit_id", "inputresource_id", "inputresource_name", "sample_name", "groupingvar_name"]))
    for i in zip(input_resources_name, groupingvars):
        print("\t".join([str(workunit_id), str(i[0][0]), i[0][1], i[1][1], i[1][2]]))

    end_time = time.time()
    print_color_msg(f"query time = {end_time - start_time:.2f} seconds")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workunit_id", type=int, help="workunit id")
    args = parser.parse_args()
    bfabric_read_samples_of_workunit(workunit_id=args.workunit_id)


if __name__ == "__main__":
    # main()
    bfabric_read_samples_of_workunit(285689)
