"""Deprecation shim — symbols moved to `bfabric.operations.dataset`."""

from __future__ import annotations

import importlib
import warnings
from typing import Any

_NEW_LOCATIONS: dict[str, tuple[str, str]] = {
    "polars_to_bfabric_dataset": ("bfabric.operations.dataset.transforms", "polars_to_dataset_dict"),
    "polars_column_to_bfabric_type": ("bfabric.operations.dataset.transforms", "_polars_column_to_bfabric_type"),
    "check_for_invalid_characters": ("bfabric.operations.dataset.validation", "check_for_invalid_characters"),
    "warn_on_trailing_spaces": ("bfabric.operations.dataset.validation", "warn_on_trailing_spaces"),
}


def __getattr__(name: str) -> Any:  # pyright: ignore[reportAny, reportExplicitAny]
    if name in _NEW_LOCATIONS:
        module_path, new_name = _NEW_LOCATIONS[name]
        warnings.warn(
            f"bfabric.experimental.upload_dataset.{name} moved to {module_path}.{new_name}; "
            "update imports — this shim will be removed in the next release.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(importlib.import_module(module_path), new_name)  # pyright: ignore[reportAny]
    if name == "bfabric_save_csv2dataset":
        raise AttributeError(
            "bfabric_save_csv2dataset has been removed. Compose the operation directly: "
            "polars.read_csv(...) → "
            "bfabric.operations.dataset.check_for_invalid_characters(...) → "
            "bfabric.operations.dataset.create_dataset(...)."
        )
    raise AttributeError(f"module 'bfabric.experimental.upload_dataset' has no attribute {name!r}")
