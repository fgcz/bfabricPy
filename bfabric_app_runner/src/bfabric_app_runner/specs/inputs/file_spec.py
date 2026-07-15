from __future__ import annotations

from typing import Literal, TYPE_CHECKING, Self

from bfabric_app_runner.specs.common_types import RelativeFilePath, AbsoluteFilePath
from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from bfabric import Bfabric


class FileSourceLocal(BaseModel):
    """A file already present on the local filesystem of the machine running the app."""

    local: AbsoluteFilePath
    """Absolute path to the source file on the local machine."""

    def get_filename(self) -> str:
        return self.local.split("/")[-1]


class FileSourceSshValue(BaseModel):
    """Location of a file on a remote host reachable over SSH."""

    host: str
    """Hostname (or ``user@host``) of the remote machine to copy the file from."""

    path: AbsoluteFilePath
    """Absolute path to the source file on the remote host."""


class FileSourceSsh(BaseModel):
    """A file to copy from a remote host over SSH."""

    ssh: FileSourceSshValue
    """The remote host and path of the source file."""

    def get_filename(self) -> str:
        return self.ssh.path.split("/")[-1]


class FileSourceHttpValue(BaseModel):
    """Location of a file to download over HTTP(S)."""

    url: str
    """URL to download the file from."""

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
    """A file to download over HTTP(S)."""

    http: FileSourceHttpValue
    """The URL and authentication scheme of the source file."""

    def get_filename(self) -> str:
        return self.http.url.split("?")[0].rstrip("/").split("/")[-1]


class FileSpec(BaseModel):
    """Stages a single file from a local path, a remote host (SSH), or an HTTP(S) URL."""

    type: Literal["file"] = "file"
    """Discriminator marking this input as a plain file."""

    source: FileSourceSsh | FileSourceLocal | FileSourceHttp
    """Where the file comes from: a local path, a remote SSH location, or an HTTP(S) URL."""

    filename: RelativeFilePath | None = None  # TODO we cannot reuse the same type
    """Target filename (relative to the chunk directory); ``None`` derives it from the source."""

    link: bool = False
    """If True, symlink the file instead of copying it; only allowed for a local source."""

    checksum: str | None = None
    """Expected checksum to verify the staged file against; ``None`` skips verification."""

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
