from __future__ import annotations

from functools import cached_property
from pathlib import Path

from bfabric.entities.core.entity import Entity


class Storage(Entity):
    ENDPOINT = "storage"

    base_path: Path = property(lambda self: Path(self.data_dict["basepath"]))

    @cached_property
    def scp_prefix(self) -> str | None:
        """SCP prefix with storage base path included."""
        protocol = self.data_dict["protocol"]
        return f"{self.data_dict['host']}:{self.data_dict['basepath']}" if protocol == "scp" else None
