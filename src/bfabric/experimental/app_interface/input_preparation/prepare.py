from __future__ import annotations

import tempfile
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.table import Table, Column

from bfabric.bfabric import Bfabric
from bfabric.entities import Resource, Dataset
from bfabric.experimental.app_interface.input_preparation._spec import (
    ResourceSpec,
    DatasetSpec,
    InputSpecType,
    InputsSpec,
)
from bfabric.experimental.app_interface.util.checksums import md5sum
from bfabric.experimental.app_interface.util.scp import scp


class PrepareInputs:
    def __init__(self, client: Bfabric, working_dir: Path, ssh_user: str | None) -> None:
        self._client = client
        self._working_dir = working_dir
        self._ssh_user = ssh_user

    def prepare_all(self, specs: list[InputSpecType]) -> None:
        for spec in specs:
            logger.debug(f"Preparing {spec}")
            if isinstance(spec, ResourceSpec):
                self.prepare_resource(spec)
            elif isinstance(spec, DatasetSpec):
                self.prepare_dataset(spec)
            else:
                raise ValueError(f"Unknown spec type: {type(spec)}")

    def clean_all(self, specs: list[InputSpecType]) -> None:
        for spec in specs:
            logger.debug(f"Cleaning {spec}")
            if isinstance(spec, ResourceSpec):
                self.clean_resource(spec)
            elif isinstance(spec, DatasetSpec):
                self.clean_dataset(spec)
            else:
                raise ValueError(f"Unknown spec type: {type(spec)}")

    def prepare_resource(self, spec: ResourceSpec) -> None:
        resource = Resource.find(id=spec.id, client=self._client)

        # determine path to copy from
        scp_uri = f"{resource.storage.scp_prefix}{resource['relativepath']}"

        # determine path to copy to
        result_name = spec.filename if spec.filename else resource["name"]
        result_path = self._working_dir / result_name

        # copy if necessary
        if result_path.exists() and md5sum(result_path) == resource["filechecksum"]:
            logger.debug(f"Skipping {resource['name']} as it already exists and has the correct checksum")
        else:
            scp(scp_uri, str(result_path), user=self._ssh_user)

            # verify checksum
            if spec.check_checksum:
                actual_checksum = md5sum(result_path)
                logger.debug(f"Checksum: expected {resource['filechecksum']}, got {actual_checksum}")
                if actual_checksum != resource["filechecksum"]:
                    raise ValueError(f"Checksum mismatch: expected {resource['filechecksum']}, got {actual_checksum}")

    def prepare_dataset(self, spec: DatasetSpec) -> None:
        dataset = Dataset.find(id=spec.id, client=self._client)
        target_path = self._working_dir / spec.filename
        target_path.parent.mkdir(exist_ok=True, parents=True)
        with tempfile.NamedTemporaryFile() as tmp_file:
            dataset.write_csv(Path(tmp_file.name), separator=spec.separator)
            tmp_file.flush()
            tmp_file.seek(0)
            if target_path.exists() and target_path.read_text() == tmp_file.read().decode():
                logger.debug(f"Skipping {spec.filename} as it already exists and has the correct content")
            else:
                tmp_file.seek(0)
                target_path.write_text(tmp_file.read().decode())

    def clean_resource(self, spec: ResourceSpec) -> None:
        filename = spec.resolve_filename(client=self._client)
        path = self._working_dir / filename
        if path.exists():
            logger.info(f"Removing {path}")
            path.unlink()
        else:
            logger.debug(f"Resource {path} does not exist")

    def clean_dataset(self, spec: DatasetSpec) -> None:
        path = self._working_dir / spec.filename
        if path.exists():
            logger.info(f"Removing {path}")
            path.unlink()
        else:
            logger.debug(f"Dataset {path} does not exist")


def prepare_folder(
    inputs_yaml: Path, target_folder: Path | None, client: Bfabric, ssh_user: str | None, action: str = "prepare"
) -> None:
    # set defaults
    inputs_yaml = inputs_yaml.absolute()
    if target_folder is None:
        target_folder = inputs_yaml.parent

    # parse the specs
    specs_list = InputsSpec.read_yaml(inputs_yaml)

    # prepare the folder
    prepare = PrepareInputs(client=client, working_dir=target_folder, ssh_user=ssh_user)
    if action == "prepare":
        prepare.prepare_all(specs=specs_list)
    elif action == "clean":
        prepare.clean_all(specs=specs_list)
    else:
        raise ValueError(f"Unknown action: {action}")


def print_input_files_list(
    inputs_yaml: Path,
    target_folder: Path,
    client: Bfabric,
) -> None:
    """Prints a list of inputs and whether they exist locally."""
    specs_list = InputsSpec.read_yaml(inputs_yaml)
    table = Table(
        Column("File"),
        Column("Input Type"),
        Column("Exists Locally"),
    )
    for spec in specs_list:
        filename = spec.resolve_filename(client=client)
        path = target_folder / filename if target_folder else Path(filename)
        table.add_row(
            str(path),
            "Resource" if isinstance(spec, ResourceSpec) else "Dataset",
            "Yes" if path.exists() else "No",
        )
    console = Console()
    console.print(table)
