from pathlib import Path
from typing import Any

import yaml
import cyclopts
from bfabric.experimental.workunit_definition import WorkunitDefinition

app = cyclopts.App()


@app.default
def dispatch(workunit_definition_path: Path, work_dir: Path) -> None:
    """Dispatches the workunit to a folder structure with 1 chunk and 1 input file."""
    workunit_definition = WorkunitDefinition.from_yaml(workunit_definition_path)
    dataset_id = workunit_definition.execution.dataset
    if dataset_id is None:
        raise ValueError("This app is a dataset-flow app, but the workunit has no input dataset.")

    # `bfabric_resource_dataset` downloads every resource the dataset lists into `input/`, next to a
    # `dataset.parquet` whose `File` column names them. Resolving it is the app-runner's job at the inputs stage,
    # so dispatch only names what it wants and never talks to B-Fabric itself.
    params = {"request_failure": workunit_definition.execution.raw_parameters.pop("request_failure") == "true"}
    inputs = [
        {"type": "bfabric_resource_dataset", "id": dataset_id, "filename": "input"},
        {"type": "static_yaml", "filename": "params.yml", "data": params},
    ]

    # Create folder structure.
    chunk_dir = work_dir / "work"
    chunk_dir.mkdir(exist_ok=True, parents=True)

    # Write output files
    _write_yaml_file(chunk_dir / "inputs.yml", {"inputs": inputs})
    _write_yaml_file(work_dir / "chunks.yml", {"chunks": [str(chunk_dir)]})


def _write_yaml_file(path: Path, content: dict[str, Any]) -> None:
    """Writes a dictionary to a yaml file."""
    path.write_text(yaml.safe_dump(content))


if __name__ == "__main__":
    app()
