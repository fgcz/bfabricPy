"""Deprecation shim — moved to private `bfabric.operations.dataset._column_types`."""

from __future__ import annotations

import importlib
import warnings
from typing import Any

_NEW_LOCATIONS: dict[str, tuple[str, str]] = {
    "DatasetColumnTypes": ("bfabric.operations.dataset._column_types", "DatasetColumnTypes"),
    "DatasetColumnTypesFile": ("bfabric.operations.dataset._column_types", "DatasetColumnTypesFile"),
    "get_dataset_column_types": ("bfabric.operations.dataset._column_types", "get_dataset_column_types"),
}


def __getattr__(name: str) -> Any:  # pyright: ignore[reportAny, reportExplicitAny]
    if name in _NEW_LOCATIONS:
        module_path, new_name = _NEW_LOCATIONS[name]
        warnings.warn(
            f"bfabric.experimental.dataset_column_types.{name} is no longer part of the public API "
            "(it backed an internal helper of upload_dataset). The shim still resolves to the new "
            f"internal location ({module_path}.{new_name}) during this release but will be removed "
            "in the next release. If you depend on this symbol externally, please open an issue so "
            "we can promote it back to public.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(importlib.import_module(module_path), new_name)  # pyright: ignore[reportAny]
    raise AttributeError(f"module 'bfabric.experimental.dataset_column_types' has no attribute {name!r}")
