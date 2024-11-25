from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity

if TYPE_CHECKING:
    from bfabric import Bfabric


class Storage(Entity):
    ENDPOINT = "storage"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    base_path = property(lambda self: Path(self.data_dict["basepath"]))

    @cached_property
    def scp_prefix(self) -> str | None:
        """SCP prefix with storage base path included."""
        protocol = self.data_dict["protocol"]
        return f"{self.data_dict['host']}:{self.data_dict['basepath']}" if protocol == "scp" else None
