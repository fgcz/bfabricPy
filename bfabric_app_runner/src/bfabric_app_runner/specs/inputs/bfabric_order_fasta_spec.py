from __future__ import annotations
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001

if TYPE_CHECKING:
    from bfabric import Bfabric


class BfabricOrderFastaSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_order_fasta"] = "bfabric_order_fasta"

    id: int
    entity: Literal["workunit", "order"]
    filename: RelativeFilePath
    required: bool = False

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename
