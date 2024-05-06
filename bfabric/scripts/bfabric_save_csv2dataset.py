#!/usr/bin/python3
"""
Author:
     Maria d'Errico <maria.derrico@fgcz.ethz.ch>


Description:
 The following script gets a csv file as input and automatically
 generates a json structure with attributes accepted by B-Fabric for 
 the creation of datasets.

 Example of input file:
  attr1, attr2
  "1", "1"
  "2", "2"
 
 Example of json output:
  obj['attribute'] = [ {'name':'attr1', 'position':1},
                       {'name':'attr2', 'position':2} ]
  obj['item'] = [ {'field': [{'value': 1, 'attributeposition':1}, 
                             {'value': 1,  'attributeposition':2 }], 
                   'position':1}, 
                  {'field': [{'value': 2, 'attributeposition':1}, 
                          {'value': 2,  'attributeposition':2 }], 
                   'position':2}]

Usage: bfabric_save_csv2dataset.py [-h] --csvfile CSVFILE --name NAME --containerid int [--workunitid int]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import TYPE_CHECKING

from bfabric.bfabric2 import Bfabric, get_system_auth

if TYPE_CHECKING:
    import pandas as pd


def csv2json(csv_file_path: Path) -> dict[str, list[dict[str, int | str | float]]]:
    """Parses a csv file and returns a B-Fabric compatible dictionary structure."""
    obj = {"item": [], "attribute": []}
    types = {int: "Integer", str: "String", float: "Float"}
    # Open the csv file in read mode and create a file object
    with csv_file_path.open(encoding="utf-8") as csv_file:
        # Creating the DictReader iterator
        csv_reader = csv.DictReader(csv_file)
        # Read individual rows of the csv file as a dictionary
        for i_row, row in enumerate(csv_reader):
            fields = []
            for attr in range(0, len(list(row.keys()))):
                if i_row == 0:
                    # Fill in attributes info
                    attr_type = type(list(row.values())[attr])
                    entry = {"name": list(row.keys())[attr], "position": attr + 1, "type": types[attr_type]}
                    obj["attribute"].append(entry)
                # Fill in values info
                fields.append({"attributeposition": attr + 1, "value": list(row.values())[attr]})
            obj["item"].append({"field": fields, "position": i_row + 1})
    return obj


def pandas2json(df: pd.DataFrame) -> dict[str, list[dict[str, int | str | float]]]:
    """Converts a pandas DataFrame to a B-Fabric compatible dictionary structure."""
    obj = {"item": [], "attribute": []}
    types = {int: "Integer", str: "String", float: "Float"}
    for i_row, row in df.iterrows():
        fields = []
        for attr in range(0, len(list(row.keys()))):
            if i_row == 0:
                # Fill in attributes info
                attr_type = type(row[attr])
                entry = {"name": list(row.keys())[attr], "position": attr + 1, "type": types[attr_type]}
                obj["attribute"].append(entry)
            # Fill in values info
            fields.append({"attributeposition": attr + 1, "value": row[attr]})
        obj["item"].append({"field": fields, "position": i_row + 1})
    return obj


def bfabric_save_csv2dataset(
    csv_file: Path, dataset_name: str, container_id: int, workunit_id: int | None = None
) -> None:
    """Creates a dataset in B-Fabric from a csv file."""
    client = Bfabric(*get_system_auth(), verbose=True)
    obj = csv2json(csv_file)
    obj["name"] = dataset_name
    obj["containerid"] = container_id
    if workunit_id is not None:
        obj["workunitid"] = workunit_id
    endpoint = "dataset"
    res = client.save(endpoint=endpoint, obj=obj)
    print(res.to_list_dict()[0])


def main() -> None:
    """Parses command line arguments and calls `bfabric_save_csv2dataset`."""
    parser = argparse.ArgumentParser(description="Create a B-Fabric dataset")
    parser.add_argument(
        "--csvfile", required=True, help="the path to the csv file to be uploaded as dataset", type=Path
    )
    parser.add_argument("--name", required=True, help="dataset name as a string")
    parser.add_argument("--containerid", type=int, required=True, help="container id")
    parser.add_argument("--workunitid", type=int, required=False, help="workunit id")
    args = parser.parse_args()
    bfabric_save_csv2dataset(
        csv_file=args.csvfile, dataset_name=args.name, container_id=args.containerid, workunit_id=args.workunitid
    )


if __name__ == "__main__":
    main()
