from __future__ import annotations

from pathlib import Path

import cyclopts
import polars as pl
import rich
import rich.prompt
from loguru import logger
from pydantic import BaseModel, model_validator
from rich.panel import Panel
from rich.pretty import Pretty

from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.operations.dataset import (
    DatasetChanges,
    check_for_invalid_characters,
    preview_dataset_update,
    update_dataset,
    warn_on_trailing_spaces,
)
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.optional_features import decorate_if_excel  # pyright: ignore[reportUnknownVariableType]


@cyclopts.Parameter(name="*")
class Params(BaseModel):
    dataset_id: int
    """The ID of the dataset to be updated."""

    file: Path
    """The file containing the updated dataset."""

    no_confirm: bool = False
    """Skip confirmation prompt."""

    forbidden_chars: str | None = ",\t"
    """Characters which are not permitted in a cell (set to empty string to deactivate)."""

    warn_trailing_spaces: bool = True
    """Whether to warn about trailing whitespace in the dataset."""


@cyclopts.Parameter(name="*")
class CsvParams(Params):
    has_header: bool = True
    """Whether the input file has a header."""
    separator: str | None = None
    """The separator to use in the CSV file."""


@cyclopts.Parameter(name="*")
class XlsxParams(Params):
    sheet_id: int | None = None
    """Index of the sheet to read (first sheet is 1)."""
    sheet_name: str | None = None
    """Name of the sheet to read."""

    @model_validator(mode="after")
    def either_sheet_id_or_name_or_neither(self):
        if self.sheet_id is None and self.sheet_name is None:
            return self
        if self.sheet_id is not None and self.sheet_name is not None:
            raise ValueError("You can only specify one of sheet_id or sheet_name.")
        if self.sheet_id is not None and self.sheet_id < 1:
            raise ValueError("sheet_id must be greater than or equal to 1.")
        if self.sheet_name is not None and self.sheet_name == "":
            raise ValueError("sheet_name must not be empty.")
        return self


cmd_dataset_update = cyclopts.App(help="Update an existing dataset in B-Fabric.")


@cmd_dataset_update.command
@use_client
def csv(params: CsvParams, *, client: Bfabric) -> None:
    """Update a dataset from a CSV file."""
    params.separator = "," if params.separator is None else params.separator
    table = pl.read_csv(params.file, separator=params.separator, has_header=params.has_header)
    _apply_update(table=table, params=params, client=client)


@cmd_dataset_update.command
@use_client
def tsv(params: CsvParams, *, client: Bfabric) -> None:
    """Update a dataset from a TSV file."""
    params.separator = "\t" if params.separator is None else params.separator
    csv(params, client=client)


@decorate_if_excel(cmd_dataset_update.command)
@use_client
def xlsx(params: XlsxParams, *, client: Bfabric) -> None:
    """Update a dataset from an Excel file."""
    table = pl.read_excel(params.file, sheet_id=params.sheet_id, sheet_name=params.sheet_name)
    _apply_update(table=table, params=params, client=client)


@cmd_dataset_update.command
@use_client
def parquet(params: Params, *, client: Bfabric) -> None:
    """Update a dataset from a Parquet file."""
    table = pl.read_parquet(params.file)
    _apply_update(table=table, params=params, client=client)


def _apply_update(table: pl.DataFrame, params: Params, client: Bfabric) -> None:
    if params.forbidden_chars:
        check_for_invalid_characters(table=table, invalid_characters=params.forbidden_chars)
    if params.warn_trailing_spaces:
        warn_on_trailing_spaces(table)

    preview = preview_dataset_update(client=client, dataset_id=params.dataset_id, table=table)
    if not preview.changes:
        logger.info("No changes detected.")
        return

    if not params.no_confirm and not _confirm_action(preview.current, preview.changes):
        return

    updated = update_dataset(client, dataset_id=params.dataset_id, table=table)
    logger.success(f"Dataset {updated.uri} updated successfully.")


def _confirm_action(dataset: Dataset, changes: DatasetChanges) -> bool:
    logger.info(f"Updating {dataset.uri}")
    container_uri = dataset.refs.uris["container"]
    if isinstance(container_uri, list):
        raise TypeError(f"Dataset {dataset.id} has multiple container references; expected exactly one.")
    container_id = container_uri.components.entity_id
    dataset_summary = {
        "id": dataset.id,
        "uri": dataset.uri,
        "name": dataset["name"],
        "containerid": container_id,
        "description": dataset.get("description"),
        "column_names": dataset.column_names,
        "column_types": dataset.column_types,
    }
    rich.print(Panel.fit(Pretty(dataset_summary), title="Existing Dataset"))
    rich.print(Panel.fit(Pretty(changes), title="Changes"))
    if not rich.prompt.Confirm.ask("Do you want to proceed with the update?"):
        logger.info("Update cancelled by user.")
        return False
    return True
