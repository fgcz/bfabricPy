import json
from enum import Enum

import polars as pl
import rich
import yaml
from rich.json import JSON
from rich.table import Table

from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.utils.cli_integration import use_client


class OutputFormat(Enum):
    TABLE = "table"
    YAML = "YAML"


def _print_table(dataframe: pl.DataFrame) -> None:
    table = Table(*dataframe.columns)
    for row in dataframe.rows():
        table.add_row(*row)
    rich.print(table)


def _print_yaml(dataframe: pl.DataFrame) -> None:
    rich.print(yaml.safe_dump(dataframe.to_dicts()))


@use_client
def cmd_dataset_show(dataset_id: int, format: OutputFormat = OutputFormat.TABLE, *, client: Bfabric) -> None:
    dataset = Dataset.find(id=dataset_id, client=client)
    dataframe = dataset.to_polars()

    if format == OutputFormat.TABLE:
        _print_table(dataframe)
    elif format == OutputFormat.YAML:
        _print_yaml(dataframe)
