from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import polars as pl

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany

if TYPE_CHECKING:
    from bfabric.entities.multiplexid import MultiplexId


class MultiplexKit(Entity):
    ENDPOINT = "multiplexkit"

    multiplex_ids: HasMany[MultiplexId] = HasMany(bfabric_field="multiplexid")

    @cached_property
    def ids(self) -> pl.DataFrame:
        return self.multiplex_ids.polars.filter(pl.col("enabled") == "true").select(
            ["name", "sequence", "reversesequence", "reversecomplementsequence", "type"]
        )
