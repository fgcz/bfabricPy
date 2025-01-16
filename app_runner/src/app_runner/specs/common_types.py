from __future__ import annotations

from typing import Annotated

from pydantic import Field

RelativeFilePath = Annotated[str, Field(pattern=r"^[^/][^:]*$")]
"""Relative file path, excluding absolute paths and ":" characters."""
