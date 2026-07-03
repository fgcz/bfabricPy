from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile
from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceHttp,
    FileSourceHttpValue,
    FileSourceLocal,
    FileSourceSsh,
    FileSpec,
)


class ResolveFileSpecs:
    def __call__(self, specs: list[FileSpec]) -> list[ResolvedFile]:
        """Converts file specifications to resolved file specifications."""
        return [
            ResolvedFile(
                source=_anonymize_http_source(spec.source),
                filename=spec.get_filename(),
                link=spec.link,
                checksum=spec.checksum,
            )
            for spec in specs
        ]


def _anonymize_http_source(
    source: FileSourceSsh | FileSourceLocal | FileSourceHttp,
) -> FileSourceSsh | FileSourceLocal | FileSourceHttp:
    """Forces user-authored HTTP sources to be fetched anonymously.

    This is the trust boundary for the bearer token: it is only ever sent to storage-derived URLs built
    by ``get_http_file_source`` (which sets ``auth="bfabric"``). An ``auth`` written in a user
    ``inputs.yml`` is dropped here so the OAuth token can never be sent to an arbitrary URL.
    """
    if isinstance(source, FileSourceHttp) and source.http.auth is not None:
        return FileSourceHttp(http=FileSourceHttpValue(url=source.http.url, auth=None))
    return source
