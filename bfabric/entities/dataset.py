from __future__ import annotations

from pathlib import Path
from typing import Any

from polars import DataFrame


class Dataset:
    """Immutable representation of a single dataset in B-Fabric.
    :param data_dict: The dictionary representation of the dataset.
    """

    def __init__(self, data_dict: dict[str, Any]) -> None:
        self._data_dict = data_dict

    @property
    def data_dict(self) -> dict[str, Any]:
        """Returns a shallow copy of the dataset dictionary."""
        return self._data_dict.copy()

    def to_polars(self) -> DataFrame:
        """Returns a Polars DataFrame representation of the dataset."""
        column_names = [x["name"] for x in self._data_dict["attribute"]]
        data = []
        for item in self._data_dict["item"]:
            row_values = [x.get("value") for x in item["field"]]
            data.append(dict(zip(column_names, row_values)))
        return DataFrame(data)

    def write_csv(self, path: Path, separator: str = ",") -> None:
        """Writes the dataset to a csv file at `path`, using the specified column `separator`."""
        self.to_polars().write_csv(path, separator=separator)

    def __repr__(self) -> str:
        """Returns the string representation of the dataset."""
        return f"Dataset({repr(self._data_dict)})"

    def __str__(self) -> str:
        """Returns the string representation of the dataset."""
        return f"Dataset({str(self._data_dict)})"
