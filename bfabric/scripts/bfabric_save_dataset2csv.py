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

from bfabric.bfabric2 import Bfabric, get_system_auth


def dataset2csv(ds, outputfile, sep=","):
    # ds.attribute contains the list of columns name
    with open(outputfile, "w") as f:
        f.write("{}\n".format(sep.join(map(lambda x: x["name"], ds["attribute"]))))
        for i in ds["item"]:
            # sort values based on the columns order in attributeposition
            fields = [(x.get("value") or "", x["attributeposition"]) for x in i["field"]]
            fields.sort(key=lambda y: int(y[1]))
            f.write("{}\n".format(sep.join([t[0] for t in fields])))


def bfabric_save_dataset2csv(dataset_id: int, out_dir: str):
    bfapp = Bfabric(*get_system_auth())
    results = bfapp.read(endpoint="dataset", obj={"id": dataset_id}).to_list_dict()
    if not results:
        raise RuntimeError("No dataset found with id '{}'".format(dataset_id))
    dataset = results[0]

    try:
        dataset2csv(dataset, "{}/dataset.csv".format(out_dir))
    except Exception:
        print("The writing process to '{}'/dataset.csv failed.".format(out_dir))
        raise


def main():
    parser = argparse.ArgumentParser(description="Save a B-Fabric dataset to a csv file")
    parser.add_argument("--id", metavar="int", required=True, help="dataset id", type=int)
    parser.add_argument(
        "--dir", required=False, default="./", help="the path to the directory where to save the csv file"
    )
    args = parser.parse_args()
    bfabric_save_dataset2csv(out_dir=args.dir, dataset_id=args.id)


if __name__ == "__main__":
    main()
