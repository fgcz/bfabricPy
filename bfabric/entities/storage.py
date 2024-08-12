from __future__ import annotations

from functools import cached_property
from typing import Any, TYPE_CHECKING

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity


class Storage(Entity):
    ENDPOINT = "storage"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    @cached_property
    def scp_prefix_no_path(self) -> str:
        """SCP prefix without storage base path included."""
        return f"{self.data_dict['host']}:"

    @cached_property
    def scp_prefix_full(self) -> str:
        """SCP prefix with storage base path included."""
        return f"{self.scp_prefix_no_path}{self.data_dict['basepath']}"
