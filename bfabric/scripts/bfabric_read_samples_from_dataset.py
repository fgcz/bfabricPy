#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
Author:
    Maria d'Errico <maria.derrico@fgcz.ethz.ch>
    13.03.2023

Description:
    The script returns the sample id for each resource in the dataset provided as input

Input: dataset id

Output: list of sample id

Usage:
   bfabric_read_samples_from_dataset.py datasetid
"""
import argparse
from bfabric.bfabric2 import Bfabric, get_system_auth


def get_table_row(client: Bfabric, relative_path: str):
    resource = client.read(endpoint="resource", obj={"relativepath": relative_path}).to_list_dict()[0]
    sample = client.read(endpoint="sample", obj={"id": resource["sample"]["id"]}).to_list_dict()[0]
    groupingvar = (sample.get("groupingvar") or {}).get("name") or ""
    return resource["workunit"]["id"], resource["id"], resource["name"], sample["name"], groupingvar


def bfabric_read_samples_from_dataset(dataset_id: int):
    client = Bfabric(*get_system_auth())
    dataset = client.read(endpoint="dataset", obj={"id": dataset_id}).to_list_dict()[0]

    positions = [a["position"] for a in dataset["attribute"] if a["name"] == "Relative Path"]
    if not positions:
        raise ValueError(f"No 'Relative Path' attribute found in the dataset {dataset_id}")
    relative_path_position = positions[0]

    print("\t".join(["workunit.id", "inputresource.id", "inputresource.name", "sample.name", "groupingvar.name"]))
    for item in dataset["item"]:
        relative_path = [
            field["value"] for field in item["field"] if field["attributeposition"] == relative_path_position
        ][0]
        workunitid, resourceid, resourcename, samplename, groupingvar = get_table_row(client, relative_path)
        print("{}\t{}\t{}\t{}\t{}".format(workunitid, resourceid, resourcename, samplename, groupingvar))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_id", type=int)
    args = parser.parse_args()
    bfabric_read_samples_from_dataset(dataset_id=args.dataset_id)


if __name__ == "__main__":
    main()
