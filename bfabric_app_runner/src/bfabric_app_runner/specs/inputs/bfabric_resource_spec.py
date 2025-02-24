from __future__ import annotations

from pathlib import Path
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001
from bfabric.entities import Resource

if TYPE_CHECKING:
    from bfabric import Bfabric


class BfabricResourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_resource"] = "bfabric_resource"

    id: int
    """B-Fabric resource ID"""

    filename: RelativeFilePath | None = None
    """Target filename to save to"""

    check_checksum: bool = True
    """Whether to check the checksum of the file, after downloading"""

    def resolve_filename(self, client: Bfabric) -> str:
        if self.filename:
            return self.filename
        else:
            resource = Resource.find(id=self.id, client=client)
            return Path(resource["relativepath"]).name
