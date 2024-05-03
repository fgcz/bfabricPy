#!/usr/bin/python3
"""
Copyright (C) 2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Maria d'Errico <maria.derrico@fgcz.ethz.ch>
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl
"""
import os

from bfabric.bfabric2 import Bfabric, get_system_auth

ROOTDIR = "/srv/www/htdocs/"


def list_not_existing_storage_dirs(client, technologyid: int=2):
    results = client.read(
        endpoint="container", obj={"technologyid": technologyid}
    ).to_list_dict()
    container_ids = sorted({x["id"] for x in results})

    for cid in container_ids:
        if not os.path.isdir(os.path.join(ROOTDIR, f"p{cid}")):
            print(cid)


def main():
    client = Bfabric(*get_system_auth(), verbose=True)
    list_not_existing_storage_dirs(client=client, technologyid=2)
    list_not_existing_storage_dirs(client=client, technologyid=4)


if __name__ == "__main__":
    main()
