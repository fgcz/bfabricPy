#!/usr/bin/env python3
"""
Copyright (C) 2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Maria d'Errico <maria.derrico@fgcz.ethz.ch>
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

from loguru import logger
from pydantic import BaseModel

from bfabric import Bfabric


class CacheData(BaseModel):
    """Content of the cache file."""

    container_ids: set[int] = set()
    checked_at: datetime.datetime = datetime.datetime(2024, 1, 1)
    query: dict[str, int | str | list[str | int]] = {
        "technologyid": [2, 4],
        "createdafter": "2024-01-01",
    }


class Cache:
    """Caches retrieval of the list of all container ids."""

    def __init__(self, path: Path, data: CacheData) -> None:
        self._path = path
        self._data = data

    @property
    def container_ids(self) -> list[int]:
        """Returns the container ids sorted."""
        return sorted(self._data.container_ids)

    @classmethod
    def load(cls, path: Path) -> Cache:
        """Returns the cache from the cache file if it exists, otherwise returns a new instance."""
        if path.exists():
            logger.info(f"Loading cache from {path}")
            data = CacheData.model_validate_json(path.read_text())
        else:
            logger.info(f"Cache file {path} does not exist. Using default values.")
            data = CacheData()
        return cls(path=path, data=data)

    def save(self) -> None:
        """Saves the cache to the cache file."""
        logger.info(f"Saving cache to {self._path}")
        with self._path.open("w") as f:
            json.dump(self._data.model_dump(mode="json"), f)

    def update(self, client: Bfabric) -> None:
        """Updates the cache with the container ids from B-Fabric."""
        now = datetime.datetime.now()
        # add some buffer to deal e.g. with miss-configured clocks
        timestamp = (self._data.checked_at - datetime.timedelta(days=1)).isoformat()
        max_results = 300 if "BFABRICPY_DEBUG" in os.environ else None
        logger.debug(f"Checking for new container ids since {timestamp} with limit {max_results}")
        result = client.read(
            endpoint="container",
            obj={**self._data.query, "createdafter": timestamp},
            return_id_only=True,
            max_results=max_results,
        )
        if len(result):
            ids = result.to_polars()["id"].unique().to_list()
            self._data.container_ids.update(ids)
        self._data.checked_at = now


def list_not_existing_storage_dirs(client: Bfabric, root_dir: Path, cache_path: Path) -> None:
    """Lists not existing storage directories for a given technology id."""
    cache = Cache.load(path=cache_path)
    cache.update(client=client)
    cache.save()

    for container_id in cache.container_ids:
        if not (root_dir / f"p{container_id}").is_dir():
            print(container_id)


def main() -> None:
    """Calls `list_not_existing_storage_dirs`."""
    client = Bfabric.connect()
    root_dir = Path("/srv/www/htdocs/")
    cache_path = Path("cache.json")
    list_not_existing_storage_dirs(client=client, root_dir=root_dir, cache_path=cache_path)


if __name__ == "__main__":
    main()
