import pytest
from bfabric_app_runner.inputs.resolve._resolve_static_file_specs import ResolveStaticFileSpecs
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec


@pytest.fixture
def resolver():
    return ResolveStaticFileSpecs()


def test_call(resolver):
    spec = StaticFileSpec(content="Hello World!", filename="hello.txt")
    result = resolver([spec, spec])
    assert len(result) == 2
    assert result[0].filename == "hello.txt"
    assert result[0].content == "Hello World!"
    assert isinstance(result[0], ResolvedStaticFile)
    assert result[1].filename == "hello.txt"
    assert result[1].content == "Hello World!"
    assert isinstance(result[1], ResolvedStaticFile)
