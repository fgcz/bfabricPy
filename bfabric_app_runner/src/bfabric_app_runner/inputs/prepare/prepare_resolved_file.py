from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bfabric.transfer import (
    Credentials,
    TransferSource,
    TransferSourceHttp,
    TransferSourceLocal,
    TransferSourceSsh,
    fetch_to_path,
)

from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceHttp,
    FileSourceLocal,
    FileSourceSsh,
)

if TYPE_CHECKING:
    from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
    from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile


def prepare_resolved_file(file: ResolvedFile, working_dir: Path, context: PrepareContext) -> None:
    """Prepares the file specified by the spec, delegating the byte transfer to ``bfabric.transfer``.

    The resolve layer produces spec ``FileSource*`` objects; this adapter maps them onto the flat
    transport types the mover understands. Behaviour is unchanged from the previous in-app-runner
    movers.
    """
    output_path = working_dir / file.filename
    source = _to_transfer_source(file.source)
    credentials = _to_credentials(context)
    fetch_to_path(source, output_path, credentials, checksum=file.checksum, link_ok=file.link)


def _to_transfer_source(source: FileSourceSsh | FileSourceLocal | FileSourceHttp) -> TransferSource:
    """Maps an app-runner spec ``FileSource*`` onto the flat ``bfabric.transfer`` transport type."""
    match source:
        case FileSourceLocal(local=local):
            return TransferSourceLocal(path=Path(local))
        case FileSourceSsh(ssh=ssh):
            return TransferSourceSsh(host=ssh.host, path=ssh.path)
        case FileSourceHttp(http=http):
            return TransferSourceHttp(url=http.url, auth=http.auth)


def _to_credentials(context: PrepareContext) -> Credentials:
    """Maps the app-runner ``PrepareContext`` onto ``bfabric.transfer.Credentials``.

    The live bearer-token provider is passed straight through, so the mover reads the token fresh on
    each request and a long transfer survives a mid-batch OAuth token refresh.
    """
    return Credentials(
        token_provider=context.token_provider,
        ssh_user=context.ssh_user,
    )
