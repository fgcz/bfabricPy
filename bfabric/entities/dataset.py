from __future__ import annotations

from pathlib import Path
from typing import Any

from polars import DataFrame

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity


class Dataset(Entity):
    """Immutable representation of a single dataset in B-Fabric.
    :param data_dict: The dictionary representation of the dataset.
    """

    ENDPOINT: str = "dataset"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    def to_polars(self) -> DataFrame:
        """Returns a Polars DataFrame representation of the dataset."""
        column_names = [x["name"] for x in self.data_dict["attribute"]]
        data = []
        for item in self.data_dict["item"]:
            row_values = [x.get("value") for x in item["field"]]
            data.append(dict(zip(column_names, row_values)))
        return DataFrame(data)

    def write_csv(self, path: Path, separator: str = ",") -> None:
        """Writes the dataset to a csv file at `path`, using the specified column `separator`."""
        self.to_polars().write_csv(path, separator=separator)
