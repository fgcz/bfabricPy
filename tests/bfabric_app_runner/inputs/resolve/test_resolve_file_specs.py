import pytest

from bfabric_app_runner.inputs.resolve._resolve_file_specs import ResolveFileSpecs
from bfabric_app_runner.specs.inputs.file_spec import FileSourceHttp, FileSourceHttpValue, FileSpec, FileSourceLocal


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


def test_call_http_source_is_forced_anonymous(resolver):
    # A user-authored FileSpec must never carry auth into the resolved source, so the OAuth bearer
    # token can never be sent to an arbitrary user-supplied URL.
    spec = FileSpec(
        source=FileSourceHttp(http=FileSourceHttpValue(url="https://attacker.example/x", auth="bfabric")),
        filename="x.txt",
    )
    result = resolver([spec])

    assert isinstance(result[0].source, FileSourceHttp)
    assert result[0].source.http.auth is None
    assert result[0].source.http.url == "https://attacker.example/x"
