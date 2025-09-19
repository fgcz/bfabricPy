from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric_app_runner.specs.inputs.file_spec import FileSourceSsh, FileSourceSshValue

if TYPE_CHECKING:
    from bfabric.entities import Resource


def get_file_source(resource: Resource) -> FileSourceSsh:
    """Get the file source for a given resource."""
    return FileSourceSsh(
        ssh=FileSourceSshValue(host=resource.storage["host"], path=str(resource.storage_absolute_path))
    )
