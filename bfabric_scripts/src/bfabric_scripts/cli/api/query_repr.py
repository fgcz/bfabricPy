from collections import defaultdict
from typing import Any, Literal, overload

from pydantic import BaseModel, model_validator


class Query(BaseModel):
    """
    A model for handling key-value query parameters.
    Validates and converts flat lists to key-value pairs.
    """

    pairs: list[tuple[str, str]] = []

    @staticmethod
    def _convert_flat_list_to_pairs(flat_list: list) -> list[tuple[str, str]]:
        """Convert a flat list to key-value pairs."""
        if flat_list and isinstance(flat_list[0], tuple):
            return flat_list
        if len(flat_list) % 2 != 0:
            msg = f"Query must have an even number of elements (key/value pairs), got {len(flat_list)}"
            raise ValueError(msg)
        return [(flat_list[i], flat_list[i + 1]) for i in range(0, len(flat_list), 2)]

    @model_validator(mode="before")
    @classmethod
    def validate_query(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"pairs": cls._convert_flat_list_to_pairs(data)}
        if isinstance(data, dict) and "pairs" in data:
            return {"pairs": cls._convert_flat_list_to_pairs(data["pairs"])}
        return data

    def drop_key_inplace(self, key: str) -> None:
        """Remove all instances of the specified key."""
        self.pairs = [(k, v) for k, v in self.pairs if k != key]

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
            for key, value in self.pairs:
                collect[key].append(value)
            if duplicates == "collect":
                return {key: (values[0] if len(values) == 1 else values) for key, values in collect.items()}
            if duplicates == "error" and len(collect) != len(self.pairs):
                duplicate_keys = [key for key, values in collect.items() if len(values) > 1]
                msg = f"Duplicate keys found in query: {duplicate_keys}"
                raise ValueError(msg)
        return dict(self.pairs)
