from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, assert_never

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInput, ResolvedFile, ResolvedStaticFile
from bfabric_app_runner.util.checksums import md5sum

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


def check_integrity(file: ResolvedInput, local_path: Path, client: Bfabric) -> IntegrityState:
    """Checks the integrity of a local file against the spec."""
    if not local_path.exists():
        return IntegrityState.Missing

    if isinstance(file, ResolvedFile):
        if file.checksum is None:
            return IntegrityState.NotChecked
        else:
            return IntegrityState.Correct if file.checksum == md5sum(local_path) else IntegrityState.Incorrect
    elif isinstance(file, ResolvedStaticFile):
        bytes_flag = "b" if isinstance(file.content, bytes) else ""
        with local_path.open(f"r{bytes_flag}") as f:
            return IntegrityState.Correct if f.read() == file.content else IntegrityState.Incorrect
    else:
        assert_never(file)
