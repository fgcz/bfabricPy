import bfabric.entities
import inspect
from enum import Enum

import polars as pl
import rich
import yaml
from rich.table import Table

from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.utils.cli_integration import use_client


class OutputFormat(Enum):
    TABLE = "table"
    YAML = "YAML"


def get_defined_entities():
    return {name: klass for name, klass in inspect.getmembers(bfabric.entities, inspect.isclass)}


def _print_table(dataframe: pl.DataFrame, types: dict[str, str], client: Bfabric) -> None:
    table = Table(*dataframe.columns)
    defined_entities = get_defined_entities()
    for row in dataframe.rows():
        out_row = []
        for col, col_value in zip(dataframe.columns, row):
            entity_class = defined_entities.get(types.get(col))
            if entity_class is not None:
                url = entity_class({"id": col_value}, client=client).web_url
                out_row.append(f"[link={url}]{col_value}[/link]")
            else:
                out_row.append(col_value)
        table.add_row(*out_row)
    rich.print(table)


def _print_yaml(dataframe: pl.DataFrame) -> None:
    rich.print(yaml.safe_dump(dataframe.to_dicts()))


@use_client
def cmd_dataset_show(dataset_id: int, format: OutputFormat = OutputFormat.TABLE, *, client: Bfabric) -> None:
    """Show a dataset in the console."""
    dataset = Dataset.find(id=dataset_id, client=client)
    types = dataset.column_types
    dataframe = dataset.to_polars()

    if format == OutputFormat.TABLE:
        _print_table(dataframe, types, client)
    elif format == OutputFormat.YAML:
        _print_yaml(dataframe)
