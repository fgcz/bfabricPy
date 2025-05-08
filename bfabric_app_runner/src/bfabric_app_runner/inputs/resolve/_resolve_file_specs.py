from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile
from bfabric_app_runner.specs.inputs.file_spec import FileSpec


class ResolveFileSpecs:
    def __call__(self, specs: list[FileSpec]) -> list[ResolvedFile]:
        """Converts file specifications to resolved file specifications."""
        return [
            ResolvedFile(source=spec.source, filename=spec.get_filename(), link=spec.link, checksum=spec.checksum)
            for spec in specs
        ]
