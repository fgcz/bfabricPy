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
from pydantic import BaseModel, field_validator
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


class DatasetChanges(BaseModel):
    column_position: list[str] = []
    """List of columns whose position has changed."""

    column_added: list[str] = []
    """List of columns added to the dataframe."""

    column_removed: list[str] = []
    """List of columns removed from the dataframe."""

    row_count: tuple[int, int] | None = None
    """Tuple of row number old, before if the number of rows has changed."""

    changed_values: list[str] = []
    """List of columns with changed values."""

    def __bool__(self) -> bool:
        """Return True if there are any changes."""
        return (
            bool(self.changed_values)
            or bool(self.column_added)
            or bool(self.column_removed)
            or bool(self.column_position)
            or self.row_count is not None
        )

    @field_validator("row_count")
    def _row_count(cls, value: tuple[int, int] | None) -> tuple[int, int] | None:
        if value is not None:
            if value[0] == value[1]:
                raise ValueError("When the tuple is set, it must be two distinct values")
            if value[0] < 0 or value[1] < 0:
                raise ValueError("Row counts must be non-negative")
        return value


def identify_changes(old_df: pl.DataFrame, new_df: pl.DataFrame) -> DatasetChanges:
    changes = DatasetChanges()

    # Check column changes
    # TODO future extensions: - dectect rename (covered by add/remove right now)
    changes.column_added = sorted(set(new_df.columns) - set(old_df.columns))
    changes.column_removed = sorted(set(old_df.columns) - set(new_df.columns))

    # check for moved columns
    common_columns = set(new_df.columns) & set(old_df.columns)
    changes.column_position = sorted(
        column for column in common_columns if new_df.columns.index(column) != old_df.columns.index(column)
    )

    if len(old_df) != len(new_df):
        changes.row_count = len(old_df), len(new_df)
    print(changes)

    # content changes
    # TODO this code assumes identical columns, if generalized it should only operate on the common ones
    # we only check which columns have changed
    for column_name in new_df.columns:
        if column_name not in changes.column_added and not new_df[column_name].equals(old_df[column_name]):
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
