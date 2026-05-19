#!/usr/bin/env python3
"""Create a B-Fabric dataset from a CSV file.

Example of input file:
  attr1, attr2
  "1", "1"
  "2", "2"

Usage: bfabric_save_csv2dataset.py [-h] --csvfile CSVFILE --name NAME --containerid int [--workunitid int]
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

import polars as pl
from loguru import logger

from bfabric import Bfabric
from bfabric.operations.dataset import (
    CreateDatasetParams,
    check_for_invalid_characters,
    create_dataset,
)
from bfabric.utils.cli_integration import use_client


@use_client
def main(*, client: Bfabric) -> None:
    parser = argparse.ArgumentParser(description="Create a B-Fabric dataset")
    _ = parser.add_argument(
        "--csvfile", required=True, type=Path, help="the path to the csv file to be uploaded as dataset"
    )
    _ = parser.add_argument("--name", required=True, help="dataset name as a string")
    _ = parser.add_argument("--containerid", type=int, required=True, help="container id")
    _ = parser.add_argument("--workunitid", type=int, required=False, help="workunit id")
    _ = parser.add_argument(
        "--sep", type=str, default=",", help="the separator to use in the csv file e.g. ',' or '\\t'"
    )
    _ = parser.add_argument("--no-header", action="store_false", dest="has_header", help="the csv file has no header")
    _ = parser.add_argument(
        "--invalid-characters",
        type=str,
        default=",\t",
        help="characters which are not permitted in a cell (set to empty string to deactivate)",
    )
    args = parser.parse_args()
    csvfile = cast(Path, args.csvfile)
    name = cast(str, args.name)
    container_id = cast(int, args.containerid)
    workunit_id = cast("int | None", args.workunitid)
    sep = cast(str, args.sep)
    has_header = cast(bool, args.has_header)
    invalid_characters = cast(str, args.invalid_characters)

    table = pl.read_csv(csvfile, separator=sep, has_header=has_header, infer_schema_length=None)
    check_for_invalid_characters(data=table, invalid_characters=invalid_characters)
    dataset = create_dataset(
        client,
        table,
        CreateDatasetParams(name=name, container_id=container_id, workunit_id=workunit_id),
    )
    logger.success(f"Dataset {dataset.uri} successfully created.")


if __name__ == "__main__":
    main()
