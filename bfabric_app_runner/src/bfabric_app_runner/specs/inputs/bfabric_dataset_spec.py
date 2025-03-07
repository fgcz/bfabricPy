from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001


class BfabricDatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_dataset"] = "bfabric_dataset"

    id: int
    """B-Fabric dataset ID"""

    filename: RelativeFilePath
    """Target filename to save to"""

    separator: Literal[",", "\t"] = ","
    """Separator for the CSV file (not relevant for Parquet)"""

    format: Literal["csv", "parquet"] = "csv"
