from __future__ import annotations

import io
from typing import TYPE_CHECKING, Annotated, Any

from polars import DataFrame
from pydantic import BaseModel, BeforeValidator

from bfabric.entities.core.entity import Entity

if TYPE_CHECKING:
    from pathlib import Path


class _AttributeData(BaseModel):
    name: str
    position: int
    type: str


def _remove_none(value: Any) -> str:  # pyright: ignore[reportAny, reportExplicitAny]
    if value is None:
        return ""
    return str(value)  # pyright: ignore[reportAny]


class _ItemDataField(BaseModel):
    value: Annotated[str, BeforeValidator(_remove_none)] = ""
    attributeposition: int


class _ItemData(BaseModel):
    field: list[_ItemDataField]


class Dataset(Entity):
    """Representation of a single dataset in B-Fabric."""

    ENDPOINT: str = "dataset"

    @property
    def _attribute_data(self) -> list[_AttributeData]:
        attributes = self["attribute"]
        if not isinstance(attributes, list) or any(not isinstance(attr, dict) for attr in attributes):
            raise ValueError("Invalid attribute data")
        return sorted([_AttributeData.model_validate(attr) for attr in attributes], key=lambda a: a.position)

    @property
    def _item_data(self) -> list[_ItemData]:
        items = self["item"]
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValueError("Invalid item data")
        return [_ItemData.model_validate(item) for item in items]

    @property
    def column_names(self) -> list[str]:
        """Returns a list of column names in the dataset."""
        return [attr.name for attr in self._attribute_data]

    @property
    def column_types(self) -> dict[str, str]:
        """Returns a dictionary mapping column names to their data types."""
        return {attr.name: attr.type for attr in self._attribute_data}

    def to_polars(self) -> DataFrame:
        """Returns a Polars DataFrame representation of the dataset."""
        column_names = self.column_names
        data = []
        for item in self._item_data:
            row_values = [item.value for item in sorted(item.field, key=lambda x: x.attributeposition)]
            data.append(dict(zip(column_names, row_values)))
        return DataFrame(data)

    def write_csv(self, path: Path, separator: str = ",") -> None:
        """Writes the dataset to a csv file at `path`, using the specified column `separator`."""
        self.to_polars().write_csv(path, separator=separator)

    def get_csv(self, separator: str = ",") -> str:
        """Returns the dataset as a csv string, using the specified column `separator`."""
        return self.to_polars().write_csv(separator=separator)

    def write_parquet(self, path: Path) -> None:
        """Writes the dataset to a parquet file at `path`."""
        self.to_polars().write_parquet(path)

    def get_parquet(self) -> bytes:
        """Returns the dataset as a parquet bytes object."""
        bytes_io = io.BytesIO()
        self.to_polars().write_parquet(bytes_io)
        return bytes_io.getvalue()
