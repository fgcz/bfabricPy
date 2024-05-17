#!/usr/bin/env python3
"""
Author:
     Maria d'Errico <maria.derrico@fgcz.ethz.ch>

     2021-12


Description:
 The following script gets the dataset id as input and automatically
 generates a csv file with the dataset content.

Usage: bfabric_save_dataset2csv.py [-h] --id DATASET_ID [--dir SCRATCHDIR]
Example: bfabric_save_dataset2csv.py --id 32335 && cat dataset.csv    
"""
from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

from bfabric import Bfabric


def dataset2csv(dataset: dict, output_path: Path, sep: str) -> None:
    """Writes the `dataset` content to csv file at `output_path`."""
    column_names = [x["name"] for x in dataset["attribute"]]
    data = []
    for item in dataset["item"]:
        row_values = [x.get("value") for x in item["field"]]
        data.append(dict(zip(column_names, row_values)))
    df = pl.DataFrame(data)
    df.write_csv(output_path, separator=sep)


def bfabric_save_dataset2csv(client: Bfabric, dataset_id: int, out_dir: Path, sep: str) -> None:
    """Saves the dataset with id `dataset_id` to a csv file at `out_dir`."""
    results = client.read(endpoint="dataset", obj={"id": dataset_id}).to_list_dict()
    if not results:
        raise RuntimeError(f"No dataset found with id '{dataset_id}'")
    dataset = results[0]
    output_path = out_dir / "dataset.csv"
    try:
        dataset2csv(dataset, output_path=output_path, sep=sep)
    except Exception:
        print(f"The writing process to '{output_path}' failed.")
        raise


def main() -> None:
    """Parses arguments and calls `bfabric_save_dataset2csv`."""
    client = Bfabric.from_config(verbose=True)
    parser = argparse.ArgumentParser(description="Save a B-Fabric dataset to a csv file")
    parser.add_argument("--id", metavar="int", required=True, help="dataset id", type=int)
    parser.add_argument(
        "--dir",
        required=False,
        type=Path,
        default=".",
        help="the path to the directory where to save the csv file",
    )
    parser.add_argument("--sep", default=",", help="the separator to use in the csv file e.g. ',' or '\\t'")
    args = parser.parse_args()
    bfabric_save_dataset2csv(client=client, out_dir=args.dir, dataset_id=args.id, sep=args.sep)


if __name__ == "__main__":
    main()
