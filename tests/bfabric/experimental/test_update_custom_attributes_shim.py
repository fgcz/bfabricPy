"""Tests that the deprecation shim for `bfabric.experimental.update_custom_attributes` keeps working."""

from __future__ import annotations

import warnings

import pytest


def test_shim_warns_and_redirects():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from bfabric.experimental.update_custom_attributes import update_custom_attributes

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    from bfabric.operations import update_custom_attributes as new

    assert update_custom_attributes is new


def test_shim_unknown_attribute_raises():
    import bfabric.experimental.update_custom_attributes as mod

    with pytest.raises(AttributeError):
        _ = mod.this_does_not_exist
