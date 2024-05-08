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
from pathlib import Path

import polars as pl

from bfabric.bfabric2 import Bfabric


def polars_to_bfabric_type(dtype: pl.DataType) -> str | None:
    if str(dtype).startswith("Int"):
        return "Integer"
    elif str(dtype).startswith("String"):
        return "String"
    elif str(dtype).startswith("Float"):
        return "Float"
    else:
        return "String"


def polars_to_bfabric_dataset(data: pl.DataFrame) -> dict[str, list[dict[str, int | str | float]]]:
    attributes = [
        {"name": col, "position": i + 1, "type": polars_to_bfabric_type(data[col].dtype)}
        for i, col in enumerate(data.columns)
    ]
    items = [
        {
            "field": [{"attributeposition": i_field + 1, "value": value} for i_field, value in enumerate(row)],
            "position": i_row + 1,
        }
        for i_row, row in enumerate(data.iter_rows())
    ]
    return {"attribute": attributes, "item": items}


def bfabric_save_csv2dataset(
    client: Bfabric,
    csv_file: Path,
    dataset_name: str,
    container_id: int,
    workunit_id: int | None,
    sep: str,
    has_header: bool,
) -> None:
    """Creates a dataset in B-Fabric from a csv file."""
    data = pl.read_csv(csv_file, separator=sep, has_header=has_header)
    obj = polars_to_bfabric_dataset(data)
    obj["name"] = dataset_name
    obj["containerid"] = container_id
    if workunit_id is not None:
        obj["workunitid"] = workunit_id
    endpoint = "dataset"
    res = client.save(endpoint=endpoint, obj=obj)
    print(res.to_list_dict()[0])


def main() -> None:
    """Parses command line arguments and calls `bfabric_save_csv2dataset`."""
    client = Bfabric.from_config(verbose=True)
    parser = argparse.ArgumentParser(description="Create a B-Fabric dataset")
    parser.add_argument(
        "--csvfile", required=True, help="the path to the csv file to be uploaded as dataset", type=Path
    )
    parser.add_argument("--name", required=True, help="dataset name as a string")
    parser.add_argument("--containerid", type=int, required=True, help="container id")
    parser.add_argument("--workunitid", type=int, required=False, help="workunit id")
    parser.add_argument("--sep", type=str, default=",", help="the separator to use in the csv file e.g. ',' or '\\t'")
    parser.add_argument("--no-header", action="store_false", dest="has_header", help="the csv file has no header")
    args = parser.parse_args()
    bfabric_save_csv2dataset(
        client=client,
        csv_file=args.csvfile,
        dataset_name=args.name,
        container_id=args.containerid,
        workunit_id=args.workunitid,
        sep=args.sep,
        has_header=args.has_header,
    )


if __name__ == "__main__":
    main()
