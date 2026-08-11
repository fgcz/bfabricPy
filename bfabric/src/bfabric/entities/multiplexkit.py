from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany

if TYPE_CHECKING:
    import polars as pl

    from bfabric.entities.multiplexid import MultiplexId


class MultiplexKit(Entity):
    ENDPOINT = "multiplexkit"

    multiplex_ids: HasMany[MultiplexId] = HasMany(bfabric_field="multiplexid")

    @cached_property
    def ids(self) -> pl.DataFrame:
        # Imported here, not at module scope: this entity is loaded by every `import bfabric`, and
        # polars is by far the heaviest dependency (~200 MB, ~70 ms). Same pattern as
        # ResultContainer.to_polars.
        import polars as pl

        return self.multiplex_ids.polars.filter(pl.col("enabled") == "true").select(
            ["name", "sequence", "reversesequence", "reversecomplementsequence", "type"]
        )
