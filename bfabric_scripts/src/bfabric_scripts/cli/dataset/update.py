from __future__ import annotations
from pathlib import Path
from bfabric.experimental.upload_dataset import polars_to_bfabric_dataset
from bfabric.experimental.dataset_changes import DatasetChanges, identify_changes
from bfabric.utils.cli_integration import use_client
from loguru import logger
import cyclopts
import polars as pl
from rich.pretty import Pretty
import rich.prompt
from rich.panel import Panel
from pydantic import BaseModel
from bfabric.entities import Dataset
from bfabric import Bfabric


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
    # check the existing dataset
    dataset = client.reader.read_id("dataset", params.dataset_id, expected_type=Dataset)
    if dataset is None:
        msg = f"Dataset with ID {params.dataset_id} not found."
        raise RuntimeError(msg)

    # read the new content
    data = pl.read_excel(params.xlsx_file)

    # confirm the changes
    changes = identify_changes(old_df=dataset.to_polars(), new_df=data)
    if not changes:
        logger.info("No changes detected.")
        return

    if not _confirm_action(dataset, changes) and not params.no_confirm:
        return

    # column types is more tricky, for now, we are not checking them
    # TODO we could check that the result of the conversion has correct types in the dict repr
    dataset_content = polars_to_bfabric_dataset(data)

    # perform the save
    _ = client.save("dataset", {"id": dataset.id, **dataset_content})
    logger.success(f"Dataset {dataset.uri} updated successfully.")


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
