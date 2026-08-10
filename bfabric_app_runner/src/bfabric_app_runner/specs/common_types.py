from __future__ import annotations

from pathlib import Path
from typing import Annotated, cast

from pydantic import AfterValidator, Field, ValidationInfo

AbsoluteFilePath = Annotated[str, Field(pattern=r"^/[^:]*$")]
"""Absolute file path, excluding ":" characters."""

RelativeFilePath = Annotated[str, Field(pattern=r"^[^/][^:]*$")]
"""Relative file path, excluding absolute paths and ":" characters."""


def _resolve_against_spec_dir(value: Path, info: ValidationInfo) -> Path:
    value = value.expanduser()
    base = cast("dict[str, Path]", info.context or {}).get("spec_dir")
    return value if value.is_absolute() or base is None else base / value


SpecRelativePath = Annotated[Path, AfterValidator(_resolve_against_spec_dir)]
"""A host path with ``~`` expanded, resolved against the directory of the spec file that declared it.

Requires validation with ``context={"spec_dir": ...}`` (see ``AppSpecTemplate.for_yaml``); without it
a relative path is left as-is.
"""
