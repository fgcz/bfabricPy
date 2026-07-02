import pytest
from pydantic import ValidationError

from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceHttp,
    FileSourceHttpValue,
    FileSourceLocal,
    FileSpec,
)


def test_http_source_get_filename_strips_query():
    source = FileSourceHttp(http=FileSourceHttpValue(url="https://host/data/x/reads.fastq.gz?token=abc"))
    assert source.get_filename() == "reads.fastq.gz"


def test_http_source_require_auth_defaults_false():
    source = FileSourceHttp(http=FileSourceHttpValue(url="https://host/data/f.txt"))
    assert source.http.require_auth is False


def test_file_spec_accepts_http_source():
    spec = FileSpec(source=FileSourceHttp(http=FileSourceHttpValue(url="https://host/f.txt")), filename="f.txt")
    assert isinstance(spec.source, FileSourceHttp)


def test_file_spec_rejects_link_for_http_source():
    with pytest.raises(ValidationError, match="Cannot link to a remote file"):
        FileSpec(source=FileSourceHttp(http=FileSourceHttpValue(url="https://host/f.txt")), filename="f.txt", link=True)


def test_file_spec_allows_link_for_local_source():
    spec = FileSpec(source=FileSourceLocal(local="/tmp/f.txt"), filename="f.txt", link=True)
    assert spec.link is True
