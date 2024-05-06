#!/usr/bin/python3

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

import argparse
from pathlib import Path

from bfabric.bfabric2 import Bfabric


def dataset2csv(dataset: dict, output_path: Path, sep: str = ",") -> None:
    """Writes the `dataset` content to csv file at `output_path`."""
    # dataset["attribute"] contains the list of columns name
    with output_path.open("w") as f:
        f.write("{}\n".format(sep.join(map(lambda x: x["name"], dataset["attribute"]))))
        for i in dataset["item"]:
            # sort values based on the columns order in attributeposition
            fields = [(x.get("value") or "", x["attributeposition"]) for x in i["field"]]
            fields.sort(key=lambda y: int(y[1]))
            print(sep.join([t[0] for t in fields]), file=f)


def bfabric_save_dataset2csv(dataset_id: int, out_dir: Path) -> None:
    """Saves the dataset with id `dataset_id` to a csv file at `out_dir`."""
    client = Bfabric.from_config(verbose=True)
    results = client.read(endpoint="dataset", obj={"id": dataset_id}).to_list_dict()
    if not results:
        raise RuntimeError(f"No dataset found with id '{dataset_id}'")
    dataset = results[0]
    output_path = out_dir / "dataset.csv"
    try:
        dataset2csv(dataset, output_path=output_path)
    except Exception:
        print(f"The writing process to '{output_path}' failed.")
        raise


def main() -> None:
    """Parses arguments and calls `bfabric_save_dataset2csv`."""
    parser = argparse.ArgumentParser(description="Save a B-Fabric dataset to a csv file")
    parser.add_argument("--id", metavar="int", required=True, help="dataset id", type=int)
    parser.add_argument(
        "--dir",
        required=False,
        type=Path,
        default=".",
        help="the path to the directory where to save the csv file",
    )
    args = parser.parse_args()
    bfabric_save_dataset2csv(out_dir=args.dir, dataset_id=args.id)


if __name__ == "__main__":
    main()
