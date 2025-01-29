from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, TYPE_CHECKING

from polars import DataFrame

from bfabric.entities.core.entity import Entity

if TYPE_CHECKING:
    from bfabric import Bfabric


class Dataset(Entity):
    """Immutable representation of a single dataset in B-Fabric.
    :param data_dict: The dictionary representation of the dataset.
    """

    ENDPOINT: str = "dataset"

    def __init__(
        self, data_dict: dict[str, Any], client: Bfabric | None = None
    ) -> None:
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

    def get_csv(self, separator: str = ",") -> str:
        """Returns the dataset as a csv string, using the specified column `separator`."""
        with tempfile.NamedTemporaryFile() as tmp_file:
            self.write_csv(Path(tmp_file.name), separator=separator)
            tmp_file.flush()
            tmp_file.seek(0)
            return tmp_file.read().decode()
