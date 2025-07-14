from pathlib import Path

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedDirectory


def prepare_resolved_directory(
    file: ResolvedDirectory,
    working_dir: Path,
    ssh_user: str | None,
) -> None:
    """Prepares the directory specified by the spec."""
    raise NotImplementedError
