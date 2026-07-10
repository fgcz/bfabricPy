from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr


class TransferSinkLocal(BaseModel):
    """A destination on the local filesystem."""

    type: Literal["local"] = "local"
    path: Path


class TransferSinkScp(BaseModel):
    """A destination on a remote host reachable over scp."""

    type: Literal["scp"] = "scp"
    host: str
    path: str


class TransferSinkTus(BaseModel):
    """A tus resumable-upload destination.

    ``endpoint``, ``metadata`` and ``token`` are all resolved by the binding (from the
    ``/rest/upload/initiate`` and create-resources calls) before this sink exists, so the mover stays
    domain-free. The tus transfer authenticates with ``token`` -- a short-lived, single-mint tus
    upload token whose ``authorization_details`` claim carries the storage path -- NOT the access
    token in :class:`~bfabric.transfer._generic.credentials.Credentials`.
    """

    type: Literal["tus"] = "tus"
    endpoint: str
    metadata: dict[str, str]
    token: SecretStr


TransferSink = Annotated[
    TransferSinkLocal | TransferSinkScp | TransferSinkTus,
    Field(discriminator="type"),
]
"""A transport-only sink description, built in code by a binding (never parsed from YAML)."""
