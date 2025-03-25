from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile
    from pathlib import Path


def prepare_resolved_static_file(file: ResolvedStaticFile, working_dir: Path) -> None:
    """Prepares the file specified by the spec.

    This operation not modify the file and thus preserve the modification time, if the file already exists
    and has the same content.
    :param file: the resolved static file
    :param working_dir: the working directory
    :raises ValueError: if the path already exists but is not a file
    """
    path = working_dir / file.filename
    path.parent.mkdir(exist_ok=True, parents=True)
    _write_file_if_changed(content=file.content, path=path)


def _write_file_if_changed(content: str | bytes, path: Path) -> None:
    binary_flag = "b" if isinstance(content, bytes) else ""

    # check if the file already exists and has the same content
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
