from __future__ import annotations

from typing import TYPE_CHECKING, Literal, assert_never

from loguru import logger

from app_runner.input_preparation.collect_annotation import prepare_annotation
from app_runner.input_preparation.integrity import IntegrityState
from app_runner.input_preparation.list_inputs import list_input_states
from app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from app_runner.specs.inputs.file_scp_spec import FileScpSpec
from app_runner.specs.inputs_spec import (
    InputSpecType,
    InputsSpec,
)
from app_runner.util.checksums import md5sum
from app_runner.util.scp import scp
from bfabric.entities import Resource, Dataset, Workunit, Order

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric


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
            elif isinstance(spec, BfabricResourceSpec):
                self.prepare_resource(spec)
            elif isinstance(spec, FileScpSpec):
                self.prepare_file_scp(spec)
            elif isinstance(spec, BfabricDatasetSpec):
                self.prepare_dataset(spec)
            elif spec.type == "bfabric_annotation":
                prepare_annotation(spec, client=self._client, working_dir=self._working_dir)
            elif isinstance(spec, BfabricOrderFastaSpec):
                self.prepare_order_fasta(spec)
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

    def prepare_resource(self, spec: BfabricResourceSpec) -> None:
        resource = Resource.find(id=spec.id, client=self._client)
        if resource is None:
            msg = f"Resource with id {spec.id} not found"
            raise ValueError(msg)

        # determine path to copy from
        # TODO as we have seen sometimes a faster approach would be to copy from the NFS mount, but this needs to be
        #      configured or recognized somehow
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

    def prepare_file_scp(self, spec: FileScpSpec) -> None:
        scp_uri = f"{spec.host}:{spec.absolute_path}"
        result_name = spec.resolve_filename(client=self._client)
        result_path = self._working_dir / result_name
        scp(scp_uri, str(result_path), user=self._ssh_user)

    def prepare_dataset(self, spec: BfabricDatasetSpec) -> None:
        dataset = Dataset.find(id=spec.id, client=self._client)
        # TODO use the new functionality Dataset.get_csv (or even go further in the refactoring)

        target_path = self._working_dir / spec.filename
        target_path.parent.mkdir(exist_ok=True, parents=True)
        dataset.write_csv(path=target_path, separator=spec.separator)

    def prepare_order_fasta(self, spec: BfabricOrderFastaSpec) -> None:
        # Find the order.
        match spec.entity:
            case "workunit":
                workunit = Workunit.find(id=spec.id, client=self._client)
                if not isinstance(workunit.container, Order):
                    raise ValueError(f"Workunit {workunit.id} is not associated with an order")
                order = workunit.container
            case "order":
                order = Order.find(id=spec.id, client=self._client)
            case _:
                assert_never(spec.entity)

        # Write the result into the file
        result_name = self._working_dir / spec.filename
        result_name.parent.mkdir(exist_ok=True, parents=True)
        with result_name.open("w") as f:
            f.write(order.data_dict.get("fastasequence", ""))


def prepare_folder(
    inputs_yaml: Path,
    target_folder: Path | None,
    client: Bfabric,
    ssh_user: str | None,
    action: Literal["prepare", "clean"] = "prepare",
) -> None:
    """Prepares the input files of a chunk folder according to the provided specs.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be downloaded.
    :param client: Bfabric client to use for obtaining metadata about the input files.
    :param ssh_user: SSH user to use for downloading the input files, should it be different from the current user.
    :param action: Action to perform.
    """
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
