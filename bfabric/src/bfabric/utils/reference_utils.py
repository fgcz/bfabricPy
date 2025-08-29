"""Utilities for working with Bfabric references."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.bfabric import Bfabric


def read_reference(client: Bfabric, reference: dict[str, Any], check: bool = True) -> dict[str, Any] | None:
    """Reads a single entity from the specified reference.
    
    :param client: the Bfabric client instance
    :param reference: a dictionary containing 'classname' and 'id' fields
    :param check: whether to raise an error if the response is not successful
    :return: the entity if exactly one result is found, None otherwise
    """
    result = client.read(reference["classname"], {"id": reference["id"]}, max_results=1, check=check)
    return result[0] if len(result) == 1 else None