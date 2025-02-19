#!/usr/bin/env python3
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

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client
from bfabric.experimental.upload_dataset import bfabric_save_csv2dataset


@use_client
def main(*, client: Bfabric) -> None:
    """Parses command line arguments and calls `bfabric_save_csv2dataset`."""
    parser = argparse.ArgumentParser(description="Create a B-Fabric dataset")
    parser.add_argument(
        "--csvfile",
        required=True,
        help="the path to the csv file to be uploaded as dataset",
        type=Path,
    )
    parser.add_argument("--name", required=True, help="dataset name as a string")
    parser.add_argument("--containerid", type=int, required=True, help="container id")
    parser.add_argument("--workunitid", type=int, required=False, help="workunit id")
    parser.add_argument(
        "--sep",
        type=str,
        default=",",
        help="the separator to use in the csv file e.g. ',' or '\\t'",
    )
    parser.add_argument(
        "--no-header",
        action="store_false",
        dest="has_header",
        help="the csv file has no header",
    )
    parser.add_argument(
        "--invalid-characters",
        type=str,
        default=",\t",
        help="characters which are not permitted in a cell (set to empty string to deactivate)",
    )
    args = parser.parse_args()
    bfabric_save_csv2dataset(
        client=client,
        csv_file=args.csvfile,
        dataset_name=args.name,
        container_id=args.containerid,
        workunit_id=args.workunitid,
        sep=args.sep,
        has_header=args.has_header,
        invalid_characters=args.invalid_characters,
    )


if __name__ == "__main__":
    main()
