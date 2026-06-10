"""Deprecation shim — symbol moved to `bfabric.operations`."""

from __future__ import annotations

import importlib
import warnings
from typing import Any

_NEW_LOCATIONS: dict[str, tuple[str, str]] = {
    "update_custom_attributes": ("bfabric.operations", "update_custom_attributes"),
}


def __getattr__(name: str) -> Any:  # pyright: ignore[reportAny, reportExplicitAny]
    if name in _NEW_LOCATIONS:
        module_path, new_name = _NEW_LOCATIONS[name]
        warnings.warn(
            f"bfabric.experimental.update_custom_attributes.{name} moved to {module_path}.{new_name}; "
            "update imports — this shim will be removed in the next release.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(importlib.import_module(module_path), new_name)  # pyright: ignore[reportAny]
    raise AttributeError(f"module 'bfabric.experimental.update_custom_attributes' has no attribute {name!r}")
