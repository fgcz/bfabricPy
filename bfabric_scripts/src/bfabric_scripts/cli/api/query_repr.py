import json
from collections import defaultdict
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from cyclopts import Parameter
from pydantic import BaseModel, model_validator

from bfabric.typing import ApiRequestDataType


class Query(BaseModel):
    """
    A model for handling key-value query parameters.
    Validates and converts flat lists to key-value pairs.
    """

    pairs: list[tuple[str, str]] = []
    json_input: Annotated[str | None, Parameter(name="--json")] = None
    """A JSON object of attribute-value pairs, merged with ``pairs``; values may be nested."""
    json_file: Annotated[Path | None, Parameter(name="--json-file")] = None
    """Path to a file containing a JSON object, as for ``--json``."""

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
            obj = cast("dict[str, object]", data)
            flat = cast("list[str] | list[tuple[str, str]]", obj["pairs"])
            return {**obj, "pairs": cls._convert_flat_list_to_pairs(flat)}  # pyright: ignore[reportUnknownMemberType]
        return data

    def drop_key_inplace(self, key: str) -> None:
        """Remove all instances of the specified key."""
        self.pairs = [(k, v) for k, v in self.pairs if k != key]

    def _json_dict(self) -> dict[str, ApiRequestDataType]:
        """Parses the JSON inputs, where ``--json`` takes precedence over ``--json-file``."""
        merged: dict[str, ApiRequestDataType] = {}
        for text in (self.json_file.read_text() if self.json_file else None, self.json_input):
            if text is None:
                continue
            parsed = cast("object", json.loads(text))
            if not isinstance(parsed, dict):
                msg = f"JSON input must be an object, got {type(parsed).__name__}"
                raise ValueError(msg)
            merged.update(cast("dict[str, ApiRequestDataType]", parsed))
        return merged

    def to_dict(self, duplicates: Literal["error", "collect"]) -> dict[str, ApiRequestDataType]:
        """Converts the query to a dictionary, mapping a repeated key to the list of its values.

        :param duplicates: ``"error"`` rejects a repeated key instead of collecting it.
        """
        collect: dict[str, list[str]] = defaultdict(list)
        for key, value in self.pairs:
            collect[key].append(value)
        if duplicates == "error" and (repeated := [key for key, values in collect.items() if len(values) > 1]):
            msg = f"Duplicate keys found in query: {repeated}"
            raise ValueError(msg)
        result: dict[str, ApiRequestDataType] = {k: (v[0] if len(v) == 1 else v) for k, v in collect.items()}
        json_dict = self._json_dict()
        if overlap := sorted(set(result) & set(json_dict)):
            msg = f"Keys specified both as pairs and in JSON input: {overlap}"
            raise ValueError(msg)
        return {**result, **json_dict}
