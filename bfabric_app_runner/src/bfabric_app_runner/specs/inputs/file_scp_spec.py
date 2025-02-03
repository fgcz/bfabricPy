from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001

if TYPE_CHECKING:
    from bfabric import Bfabric


# TODO(leo): deprecate later
class FileScpSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["file_scp"] = "file_scp"
    host: str
    absolute_path: str
    filename: RelativeFilePath | None = None

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename if self.filename else self.absolute_path.split("/")[-1]
