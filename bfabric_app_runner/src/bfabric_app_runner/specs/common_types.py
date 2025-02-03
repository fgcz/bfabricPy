from __future__ import annotations

from typing import Annotated

from pydantic import Field

AbsoluteFilePath = Annotated[str, Field(pattern=r"^/[^:]*$")]
"""Absolute file path, excluding ":" characters."""

RelativeFilePath = Annotated[str, Field(pattern=r"^[^/][^:]*$")]
"""Relative file path, excluding absolute paths and ":" characters."""
