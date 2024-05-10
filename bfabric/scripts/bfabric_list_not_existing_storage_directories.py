#!/usr/bin/python3
"""
Copyright (C) 2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Maria d'Errico <maria.derrico@fgcz.ethz.ch>
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl
"""
from __future__ import annotations
import os

from bfabric import Bfabric

ROOTDIR = "/srv/www/htdocs/"


def list_not_existing_storage_dirs(client: Bfabric, technologyid: int = 2) -> None:
    results = client.read(endpoint="container", obj={"technologyid": technologyid}).to_list_dict()
    container_ids = sorted({x["id"] for x in results})

    for cid in container_ids:
        if not os.path.isdir(os.path.join(ROOTDIR, f"p{cid}")):
            print(cid)


def main() -> None:
    client = Bfabric.from_config(verbose=True)
    list_not_existing_storage_dirs(client=client, technologyid=2)
    list_not_existing_storage_dirs(client=client, technologyid=4)


if __name__ == "__main__":
    main()
