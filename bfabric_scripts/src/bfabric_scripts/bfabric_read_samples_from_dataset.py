#!/usr/bin/env python3
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
from bfabric import Bfabric


def get_table_row(client: Bfabric, relative_path: str) -> tuple[str, int, str, str, str]:
    """Returns the row of the table with the information of the resource with the given relative path."""
    resource = client.read(endpoint="resource", obj={"relativepath": relative_path}).to_list_dict()[0]
    sample = client.read(endpoint="sample", obj={"id": resource["sample"]["id"]}).to_list_dict()[0]
    groupingvar = (sample.get("groupingvar") or {}).get("name") or ""
    return (
        resource["workunit"]["id"],
        resource["id"],
        resource["name"],
        sample["name"],
        groupingvar,
    )


def bfabric_read_samples_from_dataset(dataset_id: int) -> None:
    """Prints the workunit id, inputresource id, inputresource name, sample name and groupingvar name for each resource
    in the dataset with the given id."""
    client = Bfabric.connect()
    dataset = client.read(endpoint="dataset", obj={"id": dataset_id}).to_list_dict()[0]

    positions = [a["position"] for a in dataset["attribute"] if a["name"] == "Relative Path"]
    if not positions:
        raise ValueError(f"No 'Relative Path' attribute found in the dataset {dataset_id}")
    relative_path_position = positions[0]

    print(
        "\t".join(
            [
                "workunit.id",
                "inputresource.id",
                "inputresource.name",
                "sample.name",
                "groupingvar.name",
            ]
        )
    )
    for item in dataset["item"]:
        relative_path = [
            field["value"] for field in item["field"] if field["attributeposition"] == relative_path_position
        ][0]
        workunitid, resourceid, resourcename, samplename, groupingvar = get_table_row(client, relative_path)
        print(f"{workunitid}\t{resourceid}\t{resourcename}\t{samplename}\t{groupingvar}")


def main() -> None:
    """Parses the command line arguments and calls the function bfabric_read_samples_from_dataset."""
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_id", type=int)
    args = parser.parse_args()
    bfabric_read_samples_from_dataset(dataset_id=args.dataset_id)


if __name__ == "__main__":
    main()
