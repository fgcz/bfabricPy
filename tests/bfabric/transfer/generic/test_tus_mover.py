"""Deterministic in-process port of the tus resume proof (was a live script, scripts/prove_tus_resume.py).

Exercises upload_file's resume/offset-seeding, url-reporting and empty-file behavior against a fake
tus uploader, with no real network and no time.sleep.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from bfabric.transfer._generic import _tus_mover
from bfabric.transfer._generic._tus_mover import upload_file
from bfabric.transfer._generic.errors import TransferError

CREATED_URL = "https://tus.example/new-upload"


class FakeUploader:
    """Mimics the parts of tusclient's uploader that upload_file uses."""

    def __init__(self, file_path: str, chunk_size: int, server_offset: int, fail_at_chunk: int | None) -> None:
        self.file_size = os.path.getsize(file_path)
        self.chunk_size = chunk_size
        self.offset = 0
        self.url: str | None = None
        self._server_offset = server_offset
        self._fail_at_chunk = fail_at_chunk
        self._chunks_done = 0
        self.set_url_calls: list[str] = []

    def set_url(self, url: str) -> None:
        self.url = url
        self.set_url_calls.append(url)

    def get_offset(self) -> int:
        return self._server_offset

    def upload_chunk(self) -> None:
        # tuspy runs the creation POST (which sets self.url) before the data PATCH, so the URL exists
        # even when the chunk then fails.
        if self.url is None:
            self.url = CREATED_URL
        if self._fail_at_chunk is not None and self._chunks_done == self._fail_at_chunk:
            raise ConnectionError("simulated network drop")
        self.offset = min(self.offset + self.chunk_size, self.file_size)
        self._chunks_done += 1

    def upload(self) -> None:
        if self.url is None:
            self.url = CREATED_URL
        self.offset = 0


def _install_fake_tus(mocker, server_offset: int = 0, fail_at_chunk: int | None = None) -> dict:
    captured: dict = {}

    class _FakeTusClient:
        def __init__(self, endpoint: str) -> None:
            self.endpoint = endpoint

        def set_headers(self, headers: dict) -> None:
            captured["headers"] = headers

        def uploader(self, file_path, chunk_size, metadata, retries=0, retry_delay=0):
            up = FakeUploader(file_path, chunk_size, server_offset, fail_at_chunk)
            captured["uploader"] = up
            return up

    mocker.patch.object(_tus_mover, "TusClient", _FakeTusClient)
    return captured


def _make_file(tmp_path: Path, size: int) -> Path:
    f = tmp_path / "data.bin"
    f.write_bytes(b"\x00" * size)
    return f


def test_fresh_upload_reports_created_url_and_completes(mocker, tmp_path):
    _install_fake_tus(mocker)
    f = _make_file(tmp_path, 20)

    urls: list[str] = []
    progress: list[tuple[int, int]] = []
    outcome = upload_file(
        "https://tus.example/",
        "tok",
        f,
        {"resourceId": "1"},
        chunk_size=4,
        on_url=urls.append,
        on_progress=lambda done, total: progress.append((done, total)),
    )

    assert outcome.final_offset == 20
    assert outcome.bytes_uploaded == 20
    assert outcome.upload_url == CREATED_URL
    assert urls == [CREATED_URL]  # reported exactly once
    assert progress[-1] == (20, 20)


def test_resume_seeds_offset_from_server(mocker, tmp_path):
    # Server already has 8 of 20 bytes.
    captured = _install_fake_tus(mocker, server_offset=8)
    f = _make_file(tmp_path, 20)

    urls: list[str] = []
    progress: list[tuple[int, int]] = []
    resume_url = "https://tus.example/resume-here"
    outcome = upload_file(
        "https://tus.example/",
        "tok",
        f,
        {"resourceId": "1"},
        chunk_size=4,
        resume_url=resume_url,
        on_url=urls.append,
        on_progress=lambda done, total: progress.append((done, total)),
    )

    fake = captured["uploader"]
    # It pointed at the resume URL and seeded the local offset to the server's.
    assert fake.set_url_calls == [resume_url]
    assert progress[0] == (8, 20)  # first report is the seeded offset
    # Only the 3 remaining chunks (8->12->16->20) are sent -- NOT all 5 from offset 0. This pins down
    # the offset seeding: without it the uploader would re-send the 8 bytes the server already has.
    assert fake._chunks_done == 3
    assert outcome.final_offset == 20
    assert outcome.bytes_uploaded == 12  # only the remaining bytes
    assert outcome.upload_url == resume_url
    assert urls == [resume_url]


def test_resume_url_with_explicit_default_port_is_accepted(mocker, tmp_path):
    # The server may hand back an absolute Location that spells out the default port (:443) while the
    # endpoint omits it. That is the SAME origin per RFC 6454, so the resume must not be rejected.
    captured = _install_fake_tus(mocker, server_offset=8)
    f = _make_file(tmp_path, 20)

    resume_url = "https://tus.example:443/resume-here"
    outcome = upload_file(
        "https://tus.example/",
        "tok",
        f,
        {"resourceId": "1"},
        chunk_size=4,
        resume_url=resume_url,
    )

    fake = captured["uploader"]
    assert fake.set_url_calls == [resume_url]  # accepted, not rejected as a foreign origin
    assert outcome.final_offset == 20
    assert outcome.bytes_uploaded == 12
    assert outcome.upload_url == resume_url


def test_resume_url_from_foreign_origin_is_rejected(mocker, tmp_path):
    # A resume URL pointing at a different host must not receive the bearer token -- upload_file
    # rejects it before contacting anything.
    _install_fake_tus(mocker, server_offset=8)
    f = _make_file(tmp_path, 20)

    with pytest.raises(ValueError, match="origin"):
        upload_file(
            "https://tus.example/",
            "tok",
            f,
            {"resourceId": "1"},
            resume_url="https://evil.example/steal-my-token",
        )


def test_on_url_reported_even_when_first_chunk_fails(mocker, tmp_path):
    # The creation POST succeeds (URL registered), then the first PATCH drops.
    _install_fake_tus(mocker, fail_at_chunk=0)
    f = _make_file(tmp_path, 20)

    urls: list[str] = []
    with pytest.raises(TransferError) as excinfo:
        upload_file("https://tus.example/", "tok", f, {"resourceId": "1"}, chunk_size=4, on_url=urls.append)

    # URL was surfaced despite the failure, so the caller can still resume.
    assert urls == [CREATED_URL]
    assert isinstance(excinfo.value.__cause__, ConnectionError)


def test_zero_byte_resume_reports_url_once(mocker, tmp_path):
    _install_fake_tus(mocker)
    f = _make_file(tmp_path, 0)

    urls: list[str] = []
    resume_url = "https://tus.example/resume-empty"
    outcome = upload_file(
        "https://tus.example/", "tok", f, {"resourceId": "1"}, resume_url=resume_url, on_url=urls.append
    )

    assert urls == [resume_url]  # not fired a second time by the 0-byte branch
    assert outcome.bytes_uploaded == 0
    assert outcome.final_offset == 0


def test_empty_file_fresh_creates_upload(mocker, tmp_path):
    _install_fake_tus(mocker)
    f = _make_file(tmp_path, 0)

    urls: list[str] = []
    outcome = upload_file("https://tus.example/", "tok", f, {"resourceId": "1"}, on_url=urls.append)

    assert outcome.bytes_uploaded == 0
    assert outcome.final_offset == 0
    assert urls == [CREATED_URL]


def test_bearer_token_set_on_client(mocker, tmp_path):
    captured = _install_fake_tus(mocker)
    f = _make_file(tmp_path, 4)
    upload_file("https://tus.example/", "the-tus-token", f, {"resourceId": "1"}, chunk_size=4)
    assert captured["headers"] == {"Authorization": "Bearer the-tus-token"}
