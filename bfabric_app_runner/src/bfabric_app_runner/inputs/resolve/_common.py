from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bfabric_app_runner.specs.inputs.file_spec import FileSourceSsh, FileSourceSshValue

if TYPE_CHECKING:
    from bfabric.entities import Resource


def get_file_source_and_filename(resource: Resource, filename: str | None) -> tuple[FileSourceSsh, str]:
    """Get the file source and filename for a given resource.

    If filename is None, the original filename from the resource is used, otherwise the same value will be returned.
    """
    file_source = FileSourceSsh(
        ssh=FileSourceSshValue(
            host=resource.storage["host"], path=f"{resource.storage['basepath']}{resource['relativepath']}"
        )
    )
    filename = filename or Path(resource["relativepath"]).name
    return file_source, filename
