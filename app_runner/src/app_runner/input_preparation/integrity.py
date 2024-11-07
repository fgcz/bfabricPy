from __future__ import annotations

from enum import Enum

from bfabric.entities import Resource, Dataset
from app_runner.input_preparation.spec import InputSpecType, ResourceSpec, DatasetSpec
from app_runner.util.checksums import md5sum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric


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

    if isinstance(spec, ResourceSpec):
        return _check_resource_spec(spec, local_path, client)
    elif isinstance(spec, DatasetSpec):
        return _check_dataset_spec(spec, local_path, client)
    else:
        raise ValueError(f"Unsupported spec type: {type(spec)}")


def _check_resource_spec(spec: ResourceSpec, local_path: Path, client: Bfabric) -> IntegrityState:
    expected_checksum = Resource.find(id=spec.id, client=client)["filechecksum"]
    if expected_checksum == md5sum(local_path):
        return IntegrityState.Correct
    else:
        return IntegrityState.Incorrect


def _check_dataset_spec(spec: DatasetSpec, local_path: Path, client: Bfabric) -> IntegrityState:
    dataset = Dataset.find(id=spec.id, client=client)
    is_identical = local_path.read_text().strip() == dataset.get_csv(separator=spec.separator).strip()
    return IntegrityState.Correct if is_identical else IntegrityState.Incorrect
