from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001


class BfabricResourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_resource"] = "bfabric_resource"

    id: int
    """B-Fabric resource ID"""

    filename: RelativeFilePath | None = None
    """Target filename to save to"""

    check_checksum: bool = True
    """Whether to check the checksum of the file, after downloading"""
