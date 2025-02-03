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


class LinkingMode(str, enum.Enum):
    copy = "copy"
    link = "link"


class FileSpec(BaseModel):
    type: Literal["file"] = "file"
    source: FileSourceSsh | FileSourceLocal
    filename: RelativeFilePath | None = None
    link: LinkingMode = LinkingMode.copy

    @model_validator(mode="after")
    def validate_no_link_ssh(self) -> Self:
        if isinstance(self.source, FileSourceSsh) and self.link != LinkingMode.copy:
            raise ValueError("Cannot link to a remote file.")
        return self

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename if self.filename else self.absolute_path.split("/")[-1]
