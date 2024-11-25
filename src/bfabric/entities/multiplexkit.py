from __future__ import annotations
import polars as pl
from functools import cached_property
from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany


if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.multiplexid import MultiplexId


class MultiplexKit(Entity):
    ENDPOINT = "multiplexkit"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    multiplex_ids: HasMany[MultiplexId] = HasMany("MultiplexId", bfabric_field="multiplexid")

    @cached_property
    def ids(self) -> pl.DataFrame:
        return self.multiplex_ids.polars.filter(pl.col("enabled") == "true").select(
            ["name", "sequence", "reversesequence", "reversecomplementsequence", "type"]
        )
