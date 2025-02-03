from __future__ import annotations

from typing import Literal, TYPE_CHECKING, Self

from pydantic import BaseModel, model_validator

from bfabric_app_runner.specs.common_types import RelativeFilePath, AbsoluteFilePath  # noqa: TC001

if TYPE_CHECKING:
    from bfabric import Bfabric


class FileSourceLocal(BaseModel):
    local: AbsoluteFilePath

    def get_filename(self) -> str:
        return self.local.split("/")[-1]


class FileSourceSshValue(BaseModel):
    host: str
    path: AbsoluteFilePath


class FileSourceSsh(BaseModel):
    ssh: FileSourceSshValue

    def get_filename(self) -> str:
        return self.ssh.path.split("/")[-1]


class FileSpec(BaseModel):
    type: Literal["file"] = "file"
    source: FileSourceSsh | FileSourceLocal
    filename: RelativeFilePath | None = None
    link: bool = False

    @model_validator(mode="after")
    def validate_no_link_ssh(self) -> Self:
        if isinstance(self.source, FileSourceSsh) and self.link:
            raise ValueError("Cannot link to a remote file.")
        return self

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename if self.filename else self.source.get_filename()
