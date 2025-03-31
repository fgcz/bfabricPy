from collections import defaultdict
from typing import Any, Literal, overload

from pydantic import RootModel, field_validator


class Query(RootModel):
    """
    A model for handling key-value query parameters.
    Validates and converts flat lists to key-value pairs.
    """

    root: list[tuple[str, str]]

    @field_validator("root", mode="before")
    @classmethod
    def validate_query(cls, value: Any) -> list[tuple[str, str]]:
        """Transform a flat list input into pairs."""
        if isinstance(value, list):
            # Check if it's already a list of tuples
            if value and isinstance(value[0], tuple):
                return value

            # Handle flat list format
            if len(value) % 2 != 0:
                msg = f"Query must have an even number of elements (key/value pairs), got {len(value)}"
                raise ValueError(msg)
            return [(value[i], value[i + 1]) for i in range(0, len(value), 2)]
        return value

    @overload
    def to_dict(self, duplicates: Literal["drop"]) -> dict[str, str]: ...

    @overload
    def to_dict(self, duplicates: Literal["collect"]) -> dict[str, str | list[str]]: ...

    @overload
    def to_dict(self, duplicates: Literal["error"]) -> dict[str, str]: ...

    def to_dict(self, duplicates: Literal["drop", "error", "collect"]) -> dict[str, str] | dict[str, str | list[str]]:
        """Convert the query to a dictionary."""
        if duplicates == "collect" or duplicates == "error":
            collect: dict[str, list[str]] = defaultdict(list)
            for key, value in self.root:
                collect[key].append(value)
            if duplicates == "collect":
                return {key: (values[0] if len(values) == 1 else values) for key, values in collect.items()}
            if duplicates == "error" and len(collect) != len(self.root):
                duplicate_keys = [key for key, values in collect.items() if len(values) > 1]
                msg = f"Duplicate keys found in query: {duplicate_keys}"
                raise ValueError(msg)
        return dict(self.root)
