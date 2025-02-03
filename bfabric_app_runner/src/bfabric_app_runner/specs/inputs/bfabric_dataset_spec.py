from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001

if TYPE_CHECKING:
    from bfabric import Bfabric


class BfabricDatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_dataset"] = "bfabric_dataset"

    id: int
    """B-Fabric dataset ID"""

    filename: RelativeFilePath
    """Target filename to save to"""

    separator: Literal[",", "\t"] = ","
    """Separator for the CSV file"""

    # has_header: bool
    # invalid_characters: str = ""

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename
