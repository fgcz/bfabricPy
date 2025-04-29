#!/usr/bin/env python3
"""
Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Christian Panse <cp@fgcz.ethz.ch> 20231011
"""

import argparse
import json

from bfabric import Bfabric


def save_link(workunit_id: int, url: str, name: str) -> None:
    """Saves a link to a workunit."""
    client = Bfabric.connect()
    results = client.save(
        endpoint="link",
        obj={
            "name": name,
            "parentclassname": "workunit",
            "parentid": workunit_id,
            "url": url,
        },
    ).to_list_dict()
    print(json.dumps(results[0], indent=2))


def main() -> None:
    """Parses the command line arguments and calls `save_link`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("workunit_id", type=int, help="the workunit ID")
    parser.add_argument("link", type=str, help="the url to save")
    parser.add_argument("name", type=str, help="the name of the link")
    args = parser.parse_args()
    save_link(workunit_id=args.workunit_id, url=args.link, name=args.name)


if __name__ == "__main__":
    main()
