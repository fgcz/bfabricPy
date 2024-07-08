from __future__ import annotations

from pathlib import Path
from typing import Any

from pandas import DataFrame


class Dataset:
    """Immutable representation of a single dataset in B-Fabric.
    :param data_dict: The dictionary representation of the dataset.
    """

    def __init__(self, data_dict: dict[str, Any]) -> None:
        self._data_dict = data_dict

    @property
    def dict(self) -> dict[str, Any]:
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

    def write_csv(self, path: Path, sep: str = ",") -> None:
        """Writes the dataset to a csv file at `path`, using `sep` as the separator."""
        self.to_polars().to_csv(path, sep=sep, index=False)

    def __repr__(self) -> str:
        """Returns the string representation of the dataset."""
        return f"Dataset({repr(self._data_dict)})"

    def __str__(self) -> str:
        """Returns the string representation of the dataset."""
        return f"Dataset({str(self._data_dict)})"
