from __future__ import annotations

import datetime
from pathlib import Path

import cyclopts
from loguru import logger

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client

app = cyclopts.App()


@app.default
@use_client
def list_not_existing_storage_dirs(
    root_dir: Path = Path("/srv/www/htdocs"), cutoff_days: int = 14, *, client: Bfabric
) -> None:
    """Lists not existing storage directories for a given technology id.

    :param root_dir: Root directory where storage directories are located.
    :param cutoff_days: Number of days to look back for modified containers.
    """
    # determine cutoff date
    date = (datetime.date.today() - datetime.timedelta(days=cutoff_days)).isoformat()
    logger.info(f"Checking containers modified after cutoff date: {date}")

    # list containers with technology id 2 or 4 modified after cutoff date
    result = client.read(
        endpoint="container", obj={"technologyid": [2, 4], "modifiedafter": date}, return_id_only=True, max_results=None
    )
    container_ids = sorted(r["id"] for r in result)
    count = 0
    for container_id in container_ids:
        if not (root_dir / f"p{container_id}").is_dir():
            print(container_id)
            count += 1
    logger.info(f"Found {count} containers with not existing storage directories.")


if __name__ == "__main__":
    app()
