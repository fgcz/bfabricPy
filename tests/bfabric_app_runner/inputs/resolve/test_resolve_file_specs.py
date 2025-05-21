import pytest

from bfabric_app_runner.inputs.resolve._resolve_file_specs import ResolveFileSpecs
from bfabric_app_runner.specs.inputs.file_spec import FileSpec, FileSourceLocal


@pytest.fixture
def resolver():
    return ResolveFileSpecs()


def test_call(resolver):
    spec = FileSpec(source=FileSourceLocal(local="/scratch/test.txt"), filename=None, link=True, checksum="1234")
    result = resolver([spec, spec])

    assert len(result) == 2
    assert result[0].filename == "test.txt"
    assert result[0].source == spec.source
    assert result[0].link == True
    assert result[0].checksum == "1234"
    assert result[1] == result[0]
