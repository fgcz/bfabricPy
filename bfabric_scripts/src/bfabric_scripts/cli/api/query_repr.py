from typing import Any, Dict, List, Tuple

from pydantic import RootModel, field_validator


class Query(RootModel):
    """
    A model for handling key-value query parameters.
    Validates and converts flat lists to key-value pairs.
    """

    root: List[Tuple[str, str]]

    @field_validator("root", mode="before")
    @classmethod
    def validate_query(cls, value: Any) -> List[Tuple[str, str]]:
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

    def to_dict(self) -> Dict[str, str]:
        """Convert the query to a dictionary."""
        return dict(self.root)
