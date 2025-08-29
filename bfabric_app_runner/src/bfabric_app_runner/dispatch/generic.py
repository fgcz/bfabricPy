from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path


def write_chunks_file(out_dir: Path, chunks: list[Path]) -> None:
    """Writes the list of chunk paths to the output directory's 'chunks.yml'."""
    out_dir.mkdir(exist_ok=True, parents=True)
    with (out_dir / "chunks.yml").open("w") as f:
        data = {"chunks": [str(chunk) for chunk in chunks]}
        yaml.safe_dump(data, f)
