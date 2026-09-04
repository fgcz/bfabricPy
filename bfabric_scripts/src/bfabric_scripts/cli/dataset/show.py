import bfabric.entities
import inspect
from enum import Enum
from typing import cast

import polars as pl
import rich
import yaml
from rich.table import Table

from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.entities.core.import_entity import entity_type_of
from bfabric.entities.core.uri import EntityUri
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
                # Built from components rather than by instantiating the entity: only the id is known
                # here, and an entity with no "classname" cannot report its own URI.
                url = EntityUri.from_components(
                    bfabric_instance=client.config.base_url,
                    entity_type=entity_type_of(entity_class),
                    entity_id=int(cast("int | str", col_value)),
                )
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
    dataset = client.reader.read_id(Dataset, dataset_id)
    if not dataset:
        msg = f"Dataset with id {dataset_id!r} not found."
        raise ValueError(msg)
    types = dataset.column_types
    dataframe = dataset.to_polars()

    if format == OutputFormat.TABLE:
        _print_table(dataframe, types, client)
    elif format == OutputFormat.YAML:
        _print_yaml(dataframe)
