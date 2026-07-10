from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class TransferSourceLocal(BaseModel):
    """A file on the local filesystem."""

    type: Literal["local"] = "local"
    path: Path


class TransferSourceSsh(BaseModel):
    """A file on a remote host reachable over ssh/rsync/scp."""

    type: Literal["ssh"] = "ssh"
    host: str
    path: str


class TransferSourceHttp(BaseModel):
    """A file reachable over HTTP(S) as a whole-file stream.

    ``auth`` selects the credential scheme used for the download; it stays an enum (rather than a
    bool) so further schemes can be added without a contract change. ``None`` downloads anonymously;
    ``"bfabric"`` sends the access token from :class:`~bfabric.transfer._generic.credentials.Credentials` as a
    bearer token, and only to this URL.
    """

    type: Literal["http"] = "http"
    url: str
    auth: Literal["bfabric"] | None = None


TransferSource = Annotated[
    TransferSourceLocal | TransferSourceSsh | TransferSourceHttp,
    Field(discriminator="type"),
]
"""A transport-only source description, built in code by a binding (never parsed from YAML)."""
