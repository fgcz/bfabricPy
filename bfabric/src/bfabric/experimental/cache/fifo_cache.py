from __future__ import annotations

from collections import OrderedDict
from typing import TypeVar, Generic, TYPE_CHECKING

T = TypeVar("T")

if TYPE_CHECKING:
    from collections.abc import Hashable


class FifoCache(Generic[T]):
    """A FIFO cache with a maximum size, implemented by an OrderedDict."""

    def __init__(self, max_size: int) -> None:
        self._entries: OrderedDict[Hashable, T] = OrderedDict()
        self._max_size = max_size

    def get(self, key: Hashable) -> T | None:
        """Returns the value with the given key, if it exists, and marks it as used.

        If the key does not exist, returns None.
        """
        if key in self._entries:
            self._entries.move_to_end(key)
            return self._entries[key]

    def put(self, key: Hashable, value: T) -> None:
        """Puts a key-value pair into the cache, marking it as used."""
        if self._max_size != 0 and len(self._entries) >= self._max_size:
            self._entries.popitem(last=False)
        self._entries[key] = value

    def __contains__(self, key: Hashable) -> bool:
        """Returns whether the cache contains a key."""
        return key in self._entries
