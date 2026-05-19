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
            f"bfabric.experimental.dataset_column_types.{name} moved to {module_path}.{new_name} "
            "(now private); update imports — this shim will be removed in the next release.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(importlib.import_module(module_path), new_name)  # pyright: ignore[reportAny]
    raise AttributeError(f"module 'bfabric.experimental.dataset_column_types' has no attribute {name!r}")
