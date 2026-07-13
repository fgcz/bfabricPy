from __future__ import annotations
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from bfabric import Bfabric


class StaticFileSpec(BaseModel):
    """Writes inline text or binary content, provided in the spec itself, to a local file."""

    type: Literal["static_file"] = "static_file"

    content: str | bytes
    """The text or binary content to write."""
    filename: str
    """The target filename to write to."""

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename
