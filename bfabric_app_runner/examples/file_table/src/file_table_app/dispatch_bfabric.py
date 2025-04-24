from pathlib import Path
from typing import Any

import yaml
import cyclopts
import polars as pl
from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client
from loguru import logger

app = cyclopts.App()


# TODO this file is generally not as nice as i want it to be in the future, but i am adding it here so we do have an
#      initial version that is compatible with the currently available API (and we can also use it as a demo for
#      providing something better in the future then)


@app.default
@use_client
def dispatch(workunit_definition_path: Path, work_dir: Path, *, client: Bfabric) -> None:
    """Dispatches the workunit to a folder structure with 1 chunk and 1 input file."""
    # Get the initial information about the workunit
    workunit_definition = WorkunitDefinition.from_yaml(workunit_definition_path)
    input_bf_dataset = Dataset.find(workunit_definition.execution.dataset, client=client)
    input_df = input_bf_dataset.to_polars()
    logger.info(f"Original table: {input_df}")

    # Clean the input data frame.
    input_df = _clean_input_dataframe(input_df)
    logger.info(f"Cleaned table: {input_df}")

    # Create the input specification for each resource.
    inputs = [
        {
            "type": "bfabric_resource",
            "id": row["resource"],
            "filename": str(Path("input") / Path(row["relative_path"]).name),
        }
        for row in input_df.iter_rows(named=True)
    ]

    # Create folder structure.
    chunk_dir = work_dir / "work"
    chunk_dir.mkdir(exist_ok=True, parents=True)

    # Write output files
    _write_yaml_file(chunk_dir / "inputs.yml", {"inputs": inputs})
    _write_yaml_file(work_dir / "chunks.yml", {"chunks": [str(chunk_dir)]})


def _clean_input_dataframe(df: pl.DataFrame) -> pl.Dataframe:
    return df.clean_names(remove_special=True).select(pl.col("resource"), pl.col("relative_path"))


def _write_yaml_file(path: Path, content: dict[str, Any]) -> None:
    """Writes a dictionary to a yaml file."""
    path.write_text(yaml.safe_dump(content))


if __name__ == "__main__":
    app()
