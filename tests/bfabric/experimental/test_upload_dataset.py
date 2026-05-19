"""Tests that the deprecation shim for `bfabric.experimental.upload_dataset` keeps working."""

from __future__ import annotations

import warnings

import pytest


def test_shim_warns_and_redirects_polars_to_bfabric_dataset():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from bfabric.experimental.upload_dataset import polars_to_bfabric_dataset

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    from bfabric.operations.dataset.transforms import polars_to_dataset_dict

    assert polars_to_bfabric_dataset is polars_to_dataset_dict


def test_shim_warns_and_redirects_check_for_invalid_characters():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from bfabric.experimental.upload_dataset import check_for_invalid_characters

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    from bfabric.operations.dataset.validation import check_for_invalid_characters as new

    assert check_for_invalid_characters is new


def test_shim_warns_and_redirects_warn_on_trailing_spaces():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from bfabric.experimental.upload_dataset import warn_on_trailing_spaces

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    from bfabric.operations.dataset.validation import warn_on_trailing_spaces as new

    assert warn_on_trailing_spaces is new


def test_shim_bfabric_save_csv2dataset_raises_attribute_error():
    import bfabric.experimental.upload_dataset as mod

    with pytest.raises(AttributeError, match="bfabric_save_csv2dataset has been removed"):
        _ = mod.bfabric_save_csv2dataset


def test_shim_unknown_attribute_raises():
    import bfabric.experimental.upload_dataset as mod

    with pytest.raises(AttributeError):
        _ = mod.this_does_not_exist
