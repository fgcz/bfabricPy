from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from polars import DataFrame

from bfabric.entities.core.entity import Entity

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric import Bfabric


class Dataset(Entity):
    """Immutable representation of a single dataset in B-Fabric.
    :param data_dict: The dictionary representation of the dataset.
    """

    ENDPOINT: str = "dataset"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    @property
    def column_names(self) -> list[str]:
        """Returns a list of column names in the dataset."""
        return [attr["name"] for attr in sorted(self.data_dict["attribute"], key=lambda a: int(a["position"]))]

    @property
    def column_types(self) -> dict[str, str]:
        """Returns a dictionary mapping column names to their data types."""
        return {
            attr["name"]: attr["type"] for attr in sorted(self.data_dict["attribute"], key=lambda a: int(a["position"]))
        }

    def to_polars(self) -> DataFrame:
        """Returns a Polars DataFrame representation of the dataset."""
        column_names = self.column_names
        data = []
        for item in self.data_dict["item"]:
            row_values = [x.get("value") for x in sorted(item["field"], key=lambda x: int(x["attributeposition"]))]
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
