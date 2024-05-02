#!/usr/bin/python
# -*- coding: latin1 -*-

"""

Copyright (C) 2021 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Maria d'Errico <mderrico@fgcz.ethz.ch>

Licensed under  GPL version 3


"""
import argparse
import json
from bfabric.bfabric2 import Bfabric, get_system_auth


def bfabric_save_workunit_attribute(workunit_id: int, attribute: str, value: str):
    client = Bfabric(*get_system_auth())
    result = client.save(endpoint="workunit", obj={"id": workunit_id, attribute: value}).to_list_dict()
    print(json.dumps(result[0], indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workunit_id", type=int, help="the workunit ID")
    parser.add_argument("attribute", type=str, help="the attribute to save")
    parser.add_argument("value", type=str, help="the value to save")
    args = vars(parser.parse_args())
    bfabric_save_workunit_attribute(**args)


if __name__ == "__main__":
    main()
