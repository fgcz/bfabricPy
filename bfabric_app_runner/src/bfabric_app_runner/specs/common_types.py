from __future__ import annotations

from pathlib import Path
from typing import Annotated, cast

from pydantic import AfterValidator, Field, ValidationInfo

AbsoluteFilePath = Annotated[str, Field(pattern=r"^/[^:]*$")]
"""Absolute file path, excluding ":" characters."""

RelativeFilePath = Annotated[str, Field(pattern=r"^[^/][^:]*$")]
"""Relative file path, excluding absolute paths and ":" characters."""


def spec_dir(spec_file: Path) -> Path:
    """Returns the directory that relative paths declared in ``spec_file`` are resolved against."""
    return spec_file.resolve().parent


def _resolve_against_spec_dir(value: Path, info: ValidationInfo) -> Path:
    """Resolves ``value`` against the ``spec_dir`` validation context, if one was provided."""
    value = value.expanduser()
    context = cast("dict[str, Path] | None", info.context) or {}
    base = context.get("spec_dir")
    return value if value.is_absolute() or base is None else base / value


SpecRelativePath = Annotated[Path, AfterValidator(_resolve_against_spec_dir)]
"""A path on the machine running the app, resolved against the directory of the spec file.

``~`` is expanded and a relative path is interpreted relative to the spec file that declared it, so
a spec directory can be relocated without rewriting its paths. This requires the spec to be
validated with ``context={"spec_dir": ...}`` (see ``AppSpecTemplate.for_yaml``); without it a
relative path is left as-is.
"""
