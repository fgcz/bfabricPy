from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.experimental.workunit_definition import WorkunitDefinition


def write_workunit_definition_file(out_dir: Path, definition: WorkunitDefinition) -> None:
    """Writes the workunit definition to the output directory's 'workunit_definition.yml'."""
    out_dir.mkdir(exist_ok=True, parents=True)
    with (out_dir / "workunit_definition.yml").open("w") as f:
        yaml.safe_dump(definition.model_dump(mode="json"), f)


def write_chunks_file(out_dir: Path, chunks: list[Path]) -> None:
    """Writes the list of chunk paths to the output directory's 'chunks.yml'."""
    out_dir.mkdir(exist_ok=True, parents=True)
    with (out_dir / "chunks.yml").open("w") as f:
        data = {"chunks": [str(chunk) for chunk in chunks]}
        yaml.safe_dump(data, f)
