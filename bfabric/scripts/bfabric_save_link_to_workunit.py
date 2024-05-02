#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Christian Panse <cp@fgcz.ethz.ch> 20231011
"""
import argparse
import json
from bfabric.bfabric2 import get_system_auth, Bfabric


def save_link(workunit_id: int, url: str, name: str):
    client = Bfabric(*get_system_auth())
    results = client.save(
        endpoint="link", obj={"name": name, "parentclassname": "workunit", "parentid": workunit_id, "url": url}
    ).to_list_dict()
    print(json.dumps(results[0], indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workunit_id", type=int, help="the workunit ID")
    parser.add_argument("link", type=str, help="the url to save")
    parser.add_argument("name", type=str, help="the name of the link")
    args = parser.parse_args()
    save_link(workunit_id=args.workunit_id, url=args.link, name=args.name)


if __name__ == "__main__":
    main()
