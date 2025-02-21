from __future__ import annotations

from enum import Enum

from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.file_copy_spec import FileSpec
from bfabric_app_runner.specs.inputs.file_scp_spec import FileScpSpec
from bfabric.entities import Resource, Dataset
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec  # noqa: TC001
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec  # noqa: TC001
from bfabric_app_runner.specs.inputs.static_yaml import StaticYamlSpec
from bfabric_app_runner.util.checksums import md5sum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric
    from bfabric_app_runner.specs.inputs_spec import InputSpecType


class IntegrityState(Enum):
    """
    TODO basically this: enum(Missing, Exists(NOT_CHECKED, CORRECT, INCORRECT))
    """

    Missing = "Missing"
    NotChecked = "NotChecked"
    Correct = "Correct"
    Incorrect = "Incorrect"

    def exists(self) -> bool:
        return self != IntegrityState.Missing


def check_integrity(spec: InputSpecType, local_path: Path, client: Bfabric) -> IntegrityState:
    """Checks the integrity of a local file against the spec."""
    if not local_path.exists():
        return IntegrityState.Missing

    if isinstance(spec, BfabricResourceSpec):
        return _check_resource_spec(spec, local_path, client)
    elif isinstance(spec, BfabricDatasetSpec):
        return _check_dataset_spec(spec, local_path, client)
    elif (
        isinstance(spec, FileSpec | FileScpSpec | BfabricOrderFastaSpec | StaticYamlSpec)
        or spec.type == "bfabric_annotation"
    ):
        return IntegrityState.NotChecked
    else:
        raise ValueError(f"Unsupported spec type: {type(spec)}")


def _check_resource_spec(spec: BfabricResourceSpec, local_path: Path, client: Bfabric) -> IntegrityState:
    expected_checksum = Resource.find(id=spec.id, client=client)["filechecksum"]
    if expected_checksum == md5sum(local_path):
        return IntegrityState.Correct
    else:
        return IntegrityState.Incorrect


def _check_dataset_spec(spec: BfabricDatasetSpec, local_path: Path, client: Bfabric) -> IntegrityState:
    dataset = Dataset.find(id=spec.id, client=client)
    is_identical = local_path.read_text().strip() == dataset.get_csv(separator=spec.separator).strip()
    return IntegrityState.Correct if is_identical else IntegrityState.Incorrect
