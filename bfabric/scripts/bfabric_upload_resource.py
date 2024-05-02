#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""

Copyright (C) 2017,2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

this script takes a blob file and a workunit id as input and adds the file as resource to bfabric
"""
import argparse
import json
from pathlib import Path

from bfabric.bfabric2 import Bfabric, get_system_auth


def bfabric_upload_resource(filename: Path, workunitid: int):
    client = Bfabric(*get_system_auth())
    result = client.upload_resource(
        resource_name=filename.name,
        content=filename.read_bytes(),
        workunit_id=workunitid
    )
    print(json.dumps(result.to_list_dict(), indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="filename", type=Path)
    parser.add_argument("workunitid", help="workunitid", type=int)
    args = parser.parse_args()
    bfabric_upload_resource(filename=args.filename, workunitid=args.workunitid)


if __name__ == "__main__":
    main()
