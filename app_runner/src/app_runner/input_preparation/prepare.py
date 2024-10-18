from __future__ import annotations

from pathlib import Path

from loguru import logger

from bfabric.bfabric import Bfabric
from bfabric.entities import Resource, Dataset
from app_runner.input_preparation._spec import (
    ResourceSpec,
    DatasetSpec,
    InputSpecType,
    InputsSpec,
)
from app_runner.input_preparation.integrity import IntegrityState
from app_runner.input_preparation.list_inputs import list_input_states
from app_runner.util.checksums import md5sum
from app_runner.util.scp import scp


class PrepareInputs:
    def __init__(self, client: Bfabric, working_dir: Path, ssh_user: str | None) -> None:
        self._client = client
        self._working_dir = working_dir
        self._ssh_user = ssh_user

    def prepare_all(self, specs: list[InputSpecType]) -> None:
        # TODO ensure dataset is cached
        input_states = list_input_states(
            specs=specs, target_folder=self._working_dir, client=self._client, check_files=True
        )
        for spec, input_state in zip(specs, input_states):
            if input_state.integrity == IntegrityState.Correct:
                logger.debug(f"Skipping {spec} as it already exists and passed integrity check")
            elif isinstance(spec, ResourceSpec):
                self.prepare_resource(spec)
            elif isinstance(spec, DatasetSpec):
                self.prepare_dataset(spec)
            else:
                raise ValueError(f"Unsupported spec type: {type(spec)}")

    def clean_all(self, specs: list[InputSpecType]) -> None:
        input_states = list_input_states(
            specs=specs, target_folder=self._working_dir, client=self._client, check_files=False
        )
        for spec, input_state in zip(specs, input_states):
            if not input_state.exists:
                logger.debug(f"Skipping {spec} as it does not exist")
            else:
                logger.info(f"rm {input_state.path}")
                input_state.path.unlink()

    def prepare_resource(self, spec: ResourceSpec) -> None:
        resource = Resource.find(id=spec.id, client=self._client)

        # determine path to copy from
        scp_uri = f"{resource.storage.scp_prefix}{resource['relativepath']}"

        # determine path to copy to
        result_name = spec.filename if spec.filename else resource["name"]
        result_path = self._working_dir / result_name

        # perform the copy
        scp(scp_uri, str(result_path), user=self._ssh_user)

        # verify checksum
        if spec.check_checksum:
            actual_checksum = md5sum(result_path)
            logger.debug(f"Checksum: expected {resource['filechecksum']}, got {actual_checksum}")
            if actual_checksum != resource["filechecksum"]:
                raise ValueError(f"Checksum mismatch: expected {resource['filechecksum']}, got {actual_checksum}")

    def prepare_dataset(self, spec: DatasetSpec) -> None:
        dataset = Dataset.find(id=spec.id, client=self._client)
        # TODO use the new functionality Dataset.get_csv (or even go further in the refactoring)
        target_path = self._working_dir / spec.filename
        target_path.parent.mkdir(exist_ok=True, parents=True)
        dataset.write_csv(path=target_path, separator=spec.separator)

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
