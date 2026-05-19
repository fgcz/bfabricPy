from __future__ import annotations

from pathlib import Path

import cyclopts
import polars as pl
import rich
import rich.prompt
from loguru import logger
from pydantic import BaseModel
from rich.panel import Panel
from rich.pretty import Pretty

from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.operations.dataset import DatasetChanges, preview_dataset_update, update_dataset
from bfabric.utils.cli_integration import use_client


@cyclopts.Parameter(name="*")
class Params(BaseModel):
    dataset_id: int
    """The ID of the dataset to be updated."""

    xlsx_file: Path
    """The path to the Excel file containing the updated dataset."""

    no_confirm: bool = False
    """Skip confirmation prompt."""


@use_client
def cmd_dataset_update(params: Params, *, client: Bfabric) -> None:
    data = pl.read_excel(params.xlsx_file)

    preview = preview_dataset_update(client, params.dataset_id, data)
    if not preview.changes:
        logger.info("No changes detected.")
        return

    if not params.no_confirm and not _confirm_action(preview.current, preview.changes):
        return

    updated = update_dataset(client, params.dataset_id, data)
    logger.success(f"Dataset {updated.uri} updated successfully.")


def _confirm_action(dataset: Dataset, changes: DatasetChanges) -> bool:
    logger.info(f"Updating {dataset.uri}")
    container_uri = dataset.refs.uris["container"]
    if isinstance(container_uri, list):
        raise TypeError("should always be singular")
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
