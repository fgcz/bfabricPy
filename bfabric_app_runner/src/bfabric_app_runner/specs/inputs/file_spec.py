from __future__ import annotations

from typing import Literal, TYPE_CHECKING, Self

from bfabric_app_runner.specs.common_types import RelativeFilePath, AbsoluteFilePath
from pydantic import BaseModel, model_validator

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


class FileSourceHttpValue(BaseModel):
    url: str
    auth: Literal["bfabric"] | None = None
    """Which credential scheme to use when downloading this URL.

    ``"bfabric"`` is set only for URLs derived from a trusted B-Fabric storage access record; the
    B-Fabric OAuth bearer token is sent. ``None`` downloads anonymously — used for arbitrary
    user-supplied URLs, so the token is never sent to an untrusted host. A ``file`` spec that sets
    ``auth`` itself fails validation (see ``FileSpec.validate_no_user_supplied_auth``) rather than
    having it silently dropped, so a mistaken ``auth: bfabric`` in an ``inputs.yml`` fails loud.
    Modelled as an enum rather than a boolean so further credential schemes can be added without
    changing the wire format.
    """


class FileSourceHttp(BaseModel):
    http: FileSourceHttpValue

    def get_filename(self) -> str:
        return self.http.url.split("?")[0].rstrip("/").split("/")[-1]


class FileSpec(BaseModel):
    type: Literal["file"] = "file"
    source: FileSourceSsh | FileSourceLocal | FileSourceHttp
    filename: RelativeFilePath | None = None  # TODO we cannot reuse the same type
    link: bool = False
    checksum: str | None = None

    @model_validator(mode="after")
    def validate_no_link_remote(self) -> Self:
        if self.link and not isinstance(self.source, FileSourceLocal):
            raise ValueError("Cannot link to a remote file.")
        return self

    @model_validator(mode="after")
    def validate_no_user_supplied_auth(self) -> Self:
        if isinstance(self.source, FileSourceHttp) and self.source.http.auth is not None:
            raise ValueError(
                "'auth' is reserved for B-Fabric storage-derived URLs and cannot be set on a user-authored "
                "file spec; omit it to download the URL anonymously."
            )
        return self

    def get_filename(self) -> str:
        """Returns the filename, extracting it from the source if it was omitted."""
        return self.filename if self.filename else self.source.get_filename()

    def resolve_filename(self, client: Bfabric) -> str:
        # TODO delete
        return self.get_filename()
