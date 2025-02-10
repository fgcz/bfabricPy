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

from bfabric import Bfabric
from bfabric.entities.dataset import Dataset
from bfabric.utils.cli_integration import use_client


def bfabric_save_dataset2csv(client: Bfabric, dataset_id: int, out_dir: Path, out_filename: Path, sep: str) -> None:
    """Saves the dataset with id `dataset_id` to a csv file at `out_dir/out_filename` or `out_filename` if it's an
    absolute path.
    """
    dataset = Dataset.find(id=dataset_id, client=client)
    if not dataset:
        raise ValueError(f"Dataset with id '{dataset_id}' not found.")
    output_path = out_dir / out_filename
    try:
        dataset.write_csv(output_path, separator=sep)
    except Exception:
        print(f"The writing process to '{output_path}' failed.")
        raise


@use_client
def main(*, client: Bfabric) -> None:
    """Parses arguments and calls `bfabric_save_dataset2csv`."""
    parser = argparse.ArgumentParser(description="Save a B-Fabric dataset to a csv file")
    parser.add_argument("--id", metavar="int", required=True, help="dataset id", type=int)
    parser.add_argument(
        "--dir",
        type=Path,
        default=".",
        help="the path to the directory where to save the csv file",
    )
    parser.add_argument(
        "--file",
        default="dataset.csv",
        help="the name of the csv file to save the dataset content",
    )
    parser.add_argument(
        "--sep",
        default=",",
        help="the separator to use in the csv file e.g. ',' or '\\t'",
    )
    args = parser.parse_args()
    bfabric_save_dataset2csv(
        client=client,
        out_dir=args.dir,
        out_filename=args.file,
        dataset_id=args.id,
        sep=args.sep,
    )


if __name__ == "__main__":
    main()
