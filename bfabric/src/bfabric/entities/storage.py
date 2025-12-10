from __future__ import annotations

from functools import cached_property
from pathlib import Path

from bfabric.entities.core.entity import Entity


class Storage(Entity):
    ENDPOINT = "storage"

    @property
    def base_path(self) -> Path:
        str_path = self.data_dict["basepath"]
        if not isinstance(str_path, str):
            raise ValueError("basepath must be a string")
        return Path(str_path)

    @cached_property
    def scp_prefix(self) -> str | None:
        """SCP prefix with storage base path included."""
        protocol = self.data_dict["protocol"]
        return f"{self.data_dict['host']}:{self.data_dict['basepath']}" if protocol == "scp" else None
