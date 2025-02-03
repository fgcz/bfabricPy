from __future__ import annotations

import enum
from typing import Literal, TYPE_CHECKING, Self

from pydantic import BaseModel, model_validator

from app_runner.specs.common_types import RelativeFilePath, AbsoluteFilePath  # noqa: TC001

if TYPE_CHECKING:
    from bfabric import Bfabric


class FileSourceLocal(BaseModel):
    local: AbsoluteFilePath


class FileSourceSshValue(BaseModel):
    host: str
    path: AbsoluteFilePath


class FileSourceSsh(BaseModel):
    ssh: FileSourceSshValue


# TODO this is a bit rough -> because it is distinct for linking /also the tool used does not
#    inform the type of resource so maybe it does not belong into the spec after all ,
#    unlike "link" since this a different operation
class FileMode(enum.Enum):
    try_rsync = "try_rsync"
    force_rsync = "force_rsync"
    force_scp = "force_scp"
    force_cp = "force_cp"


class FileSpec(BaseModel):
    type: Literal["file"] = "file"
    source: FileSourceSsh | FileSourceLocal
    target_type: Literal["copy", "link"] = "copy"
    filename: RelativeFilePath | None = None
    mode: FileMode = FileMode.try_rsync

    @model_validator(mode="after")
    def validate_no_link_ssh(self) -> Self:
        if isinstance(self.source, FileSourceSsh) and self.target_type == "link":
            raise ValueError("Cannot link to a remote file.")
        return self

    @model_validator(mode="after")
    def validate_file_mode(self) -> Self:
        if self.mode == FileMode.force_scp and isinstance(self.source, FileSourceLocal):
            raise ValueError("Cannot force scp for local files.")
        if self.mode == FileMode.force_cp and isinstance(self.source, FileSourceSsh):
            raise ValueError("Cannot force cp for remote files.")
        return self

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename if self.filename else self.absolute_path.split("/")[-1]
