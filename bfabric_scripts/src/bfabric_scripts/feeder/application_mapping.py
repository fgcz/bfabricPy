from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
import polars as pl
from pydantic import BaseModel
from bfabric.entities.core.uri import EntityUri
import datetime
from boltons.fileutils import atomic_save

if TYPE_CHECKING:
    from bfabric import Bfabric


def retrieve_application_mapping(client: Bfabric, system_config: SystemConfig) -> pl.DataFrame:
    """Returns the up to date application mapping.

    The table contains columns:
        - application_id: int - the application's unique identifier
        - application_uri: str - the application's URI (identifies it uniquely accross B-Fabric instances)
        - application_name: str - the application's name
        - technology_id: int - the technology's unique identifier
        - created: datetime - the date and time the application was created
        - modified: datetime - the date and time the application was last modified
    """
    results_df = client.read(
        endpoint="application",
        obj={
            "type": "import",
            "technologyid": system_config.technology_ids,
            "storageid": system_config.storage_id,
            "enabled": True,
            "hidden": False,
        },
        max_results=None,
        return_id_only=False,
    ).to_polars(flatten=True)

    exploded_df = results_df.select(
        pl.col("id").alias("application_id"),
        pl.col("id")
        .map_elements(
            lambda id: EntityUri.from_components(
                bfabric_instance=client.config.base_url, entity_type="application", entity_id=id
            ),
            return_dtype=pl.Utf8,
        )
        .alias("application_uri"),
        pl.col("name").alias("application_name"),
        pl.col("technology"),
        pl.col("created"),
        pl.col("modified"),
    ).explode("technology")

    # TODO I think these are mostly apps which should be deactivated but we omit every app which does not match the following regex
    filtered_df = exploded_df.filter(pl.col("application_name").str.contains(r"^[a-zA-Z0-9_]+$"))
    return filtered_df


class SystemConfig(BaseModel):
    storage_id: int = 2
    technology_ids: list[int] = [2, 4]


def load_or_update_cache(path: Path, client: Bfabric, config: SystemConfig, ttl_hours: float = 24.0) -> pl.DataFrame:
    requires_update = True
    if path.exists():
        # check the timestamp first
        st_result = path.stat()
        if (
            datetime.datetime.now() - datetime.datetime.fromtimestamp(st_result.st_mtime)
        ).total_seconds() / 3600 <= ttl_hours:
            requires_update = False

    if requires_update:
        df = retrieve_application_mapping(client, config)
        with atomic_save(str(path)) as file:
            df.write_csv(file, separator="\t")
        return df
    else:
        return pl.read_csv(path, separator="\t")
