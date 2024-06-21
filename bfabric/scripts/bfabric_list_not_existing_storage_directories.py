#!/usr/bin/env python3
"""
Copyright (C) 2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Maria d'Errico <maria.derrico@fgcz.ethz.ch>
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3
"""
from __future__ import annotations

from pathlib import Path

from bfabric import Bfabric


def list_not_existing_storage_dirs(client: Bfabric, root_dir: Path, technology_id: int | list[int]) -> None:
    """Lists not existing storage directories for a given technology id."""
    results = client.read(endpoint="container", obj={"technologyid": technology_id}, return_id_only=True)
    container_ids = sorted({x["id"] for x in results})

    for container_id in container_ids:
        if not (root_dir / f"p{container_id}").is_dir():
            print(container_id)


def main() -> None:
    """Parses CLI arguments and calls `list_not_existing_storage_dirs`."""
    client = Bfabric.from_config(verbose=True)
    root_dir = Path("/srv/www/htdocs/")
    list_not_existing_storage_dirs(client=client, root_dir=root_dir, technology_id=[2, 4])


if __name__ == "__main__":
    main()
