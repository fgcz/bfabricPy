from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bfabric_app_runner.input_preparation.integrity import IntegrityState
from bfabric_app_runner.input_preparation.list_inputs import list_input_states
from bfabric_app_runner.inputs.resolve.resolver import Resolver
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from bfabric_app_runner.specs.inputs.file_spec import FileSpec
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec
from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec
from bfabric_app_runner.specs.inputs_spec import (
    InputSpecType,
    InputsSpec,
)
from loguru import logger

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric
    from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInputs


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
            elif isinstance(spec, FileSpec):
                self.prepare_file_spec(spec)
            elif isinstance(spec, BfabricDatasetSpec):
                self.prepare_dataset(spec)
            elif isinstance(spec, StaticYamlSpec):
                self.prepare_static_yaml(spec)
            elif spec.type == "bfabric_annotation":
                raise NotImplementedError
                # prepare_annotation(spec, client=self._client, working_dir=self._working_dir)
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


def prepare_folder(
    inputs_yaml: Path,
    target_folder: Path | None,
    client: Bfabric,
    ssh_user: str | None,
    filter: str | None,
    action: Literal["prepare", "clean"] = "prepare",
) -> None:
    """Prepares the input files of a chunk folder according to the provided specs.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be downloaded.
    :param client: Bfabric client to use for obtaining metadata about the input files.
    :param ssh_user: SSH user to use for downloading the input files, should it be different from the current user.
    :param filter: only this input file will be prepared.
    :param action: Action to perform.
    """
    # set defaults
    inputs_yaml = inputs_yaml.absolute()
    if target_folder is None:
        target_folder = inputs_yaml.parent

    # parse the specs
    inputs_spec = InputsSpec.read_yaml(inputs_yaml)

    if filter:
        # TODO this will require filenames which we only have once its resolved
        raise NotImplementedError
        # inputs_spec = inputs_spec.apply_filter(filter, client=client)
        # if not inputs_spec.inputs:
        #    raise ValueError(f"Filter {filter} did not match any input files")

    # resolve the specs
    resolver = Resolver(client=client)
    input_files = resolver.resolve(specs=inputs_spec.inputs)

    # prepare the folder
    # prepare = PrepareInputs(client=client, working_dir=target_folder, ssh_user=ssh_user)
    if action == "prepare":
        prepare_input_files(input_files=input_files, working_dir=target_folder, ssh_user=ssh_user)
    elif action == "clean":
        raise NotImplementedError
    else:
        raise ValueError(f"Unknown action: {action}")


def prepare_input_files(input_files: ResolvedInputs, working_dir: Path, ssh_user: str | None) -> None:
    """Prepares the input files in the working directory according to the provided specs."""
    for input_file in input_files.files:
        match input_file:
            case FileSpec() as file_spec:
                _prepare_file_spec(spec=file_spec, path=working_dir, ssh_user=ssh_user)
            case StaticFileSpec(content=content, filename=filename):
                _write_file_if_changed(content=content, path=working_dir / filename)


def _prepare_file_spec(spec: FileSpec, path: Path, ssh_user: str | None) -> None:
    raise NotImplementedError


def _write_file_if_changed(content: str | bytes, path: Path) -> None:
    binary_flag = "b" if isinstance(content, bytes) else ""

    # ensure dir exists
    path.parent.mkdir(exist_ok=True, parents=True)

    # check if the file exists
    if path.exists():
        if not path.is_file():
            msg = f"Path {path} exists but is not a file"
            raise ValueError(msg)
        with path.open(f"r{binary_flag}") as f:
            existing_content = f.read()
        if existing_content == content:
            logger.debug(f"Skipping {path} as it already exists and has the same content")
            return

    # write the file
    with path.open(f"w{binary_flag}") as f:
        f.write(content)
    logger.info(f"Writen to {path}")
