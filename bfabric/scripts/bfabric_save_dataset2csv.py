#!/usr/bin/python3

"""
Author:
     Maria d'Errico <maria.derrico@fgcz.ethz.ch>


Description:
 The following script gets the dataset id as input and automatically
 generates a csv file with the dataset content.

Usage: bfabric_save_dataset2csv.py [-h] --id DATASET_ID [--dir SCRATCHDIR]
"""

import sys
from bfabric import Bfabric

def dataset2csv(ds, outputfile, sep=","):
    # ds.attribute contains the list of columns name
    with open(outputfile, "w") as f:
        f.write("{}\n".format(sep.join(map(lambda x: x.name, ds.attribute))))
        f.write(sep.join([x.value for i in ds.item for x in i.field]))


def main(dataset_id, scratchdir):
    bfapp = Bfabric()
    try:
        query_obj = {'id': dataset_id}
        ds = bfapp.read_object(endpoint='dataset', obj=query_obj)[0]
    except:
        print("No input dataset found")
        raise

    try:
        dataset2csv(ds, "{}/dataset.csv".format(scratchdir))
    except:
        print("The writing process to '{}'/dataset.csv failed.".format(scratchdir))
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Save a B-Fabric dataset to a csv file')
    parser.add_argument('--id', metavar='int', required=True,
            help='dataset id')
    parser.add_argument('--dir', required=False, default='./',
            help='the path to the directory where to save the csv file')
    args = parser.parse_args()
    main(scratchdir = args.dir, dataset_id = args.id)

