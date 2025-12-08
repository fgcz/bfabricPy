from __future__ import annotations
from pathlib import Path
from bfabric.experimental.upload_dataset import polars_to_bfabric_dataset
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


class DatasetChanges(BaseModel):
    add_column: list[str] = []
    """List of columns added to the dataframe."""

    remove_column: list[str] = []
    """List of columns removed from the dataframe."""

    changed_values: list[str] = []
    """List of columns with changed values."""

    def __bool__(self) -> bool:
        return bool(self.changed_values) or bool(self.add_column) or bool(self.remove_column)


def identify_changes(old_df: pl.DataFrame, new_df: pl.DataFrame) -> DatasetChanges:
    changes = DatasetChanges()

    # TODO ordering is not checked?
    changes.add_column = sorted(set(new_df.columns) - set(old_df.columns))
    changes.remove_column = sorted(set(old_df.columns) - set(new_df.columns))

    if len(old_df) != len(new_df):
        # TODO report instead of fail and handle in script later
        msg = f"Row count mismatch: {len(old_df)=} != {len(new_df)=}"
        raise ValueError(msg)

    # content changes
    # TODO this code assumes identical columns, if generalized it should only operate on the common ones
    # we only check which columns have changed
    for column_name in new_df.columns:
        if column_name not in changes.add_column and not new_df[column_name].equals(old_df[column_name]):
            changes.changed_values.append(column_name)

    return changes


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

    if not _confirm_action(dataset, changes):
        return

    # column types is more tricky, for now, we are not checking them
    # TODO we could check that the result of the conversion has correct types in the dict repr
    dataset_content = polars_to_bfabric_dataset(data)

    # TODO confirm maybe highlight the changes which will be performed

    # perform the save
    _ = client.save("dataset", {"id": dataset.id, **dataset_content})
    logger.success(f"Dataset {dataset.uri} updated successfully.")


def _confirm_action(dataset: Dataset, changes: DatasetChanges) -> bool:
    logger.info(f"Updating {dataset.uri}")
    dataset_summary = {
        "id": dataset.id,
        "uri": dataset.uri,
        "name": dataset["name"],
        "containerid": dataset["container"]["id"],
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
