"""Unit tests for :class:`bfabric.transfer.resume_cache.ResumeCache`."""

from __future__ import annotations

import json

import pytest

from bfabric.transfer.resume_cache import DEFAULT_RESUME_TTL_SECONDS, ResumeCache

ENDPOINT = "https://tus.example/files/"
URL = "https://tus.example/files/abc123"
CONTAINER_ID = 100
APPLICATION_ID = 5


def _store(cache, *, md5, url=URL, workunit_id=900, resource_id=700, container_id=CONTAINER_ID):
    """Store an entry, defaulting the records a resumed upload must continue into."""
    cache.store(
        md5=md5,
        url=url,
        workunit_id=workunit_id,
        resource_id=resource_id,
        container_id=container_id,
        application_id=APPLICATION_ID,
    )


def _url(cache, *, md5, endpoint=ENDPOINT, container_id=CONTAINER_ID):
    """The saved URL for ``md5``, or None -- the shape most of these tests assert on."""
    entry = cache.lookup(md5=md5, container_id=container_id, application_id=APPLICATION_ID, endpoint=endpoint)
    return entry.url if entry is not None else None


@pytest.fixture
def cache_path(tmp_path):
    return tmp_path / "resume.json"


@pytest.fixture
def clock():
    """A mutable fake clock, so TTL expiry is exercised without sleeping."""

    class Clock:
        now = 1_000_000.0

        def __call__(self) -> float:
            return self.now

    return Clock()


class TestRoundTrip:
    def test_stored_url_is_returned_for_the_same_md5_and_endpoint(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="deadbeef", url=URL)

        assert _url(ResumeCache(cache_path, now=clock), md5="deadbeef", endpoint=ENDPOINT) == URL

    def test_unknown_md5_returns_none(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="deadbeef", url=URL)

        assert _url(cache, md5="cafe", endpoint=ENDPOINT) is None

    def test_missing_file_is_a_miss_not_an_error(self, cache_path, clock):
        assert _url(ResumeCache(cache_path, now=clock), md5="deadbeef", endpoint=ENDPOINT) is None

    def test_corrupt_file_is_a_miss_not_an_error(self, cache_path, clock):
        cache_path.write_text("{not json")

        assert _url(ResumeCache(cache_path, now=clock), md5="deadbeef", endpoint=ENDPOINT) is None

    def test_storing_a_second_file_keeps_the_first(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", url=URL)
        _store(cache, md5="bbb", url=URL + "-2")

        assert _url(cache, md5="aaa", endpoint=ENDPOINT) == URL
        assert _url(cache, md5="bbb", endpoint=ENDPOINT) == URL + "-2"

    def test_restoring_the_same_md5_overwrites(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", url=URL)
        _store(cache, md5="aaa", url=URL + "-new")

        assert _url(cache, md5="aaa", endpoint=ENDPOINT) == URL + "-new"


class TestInvalidation:
    def test_cross_origin_entry_is_not_returned(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", url=URL)

        # A different host: same_origin refuses to send the bearer token there, so it is unusable.
        assert _url(cache, md5="aaa", endpoint="https://other.example/files/") is None

    def test_implicit_default_port_is_the_same_origin(self, cache_path, clock):
        # The saved URL omits the port, the endpoint states it explicitly: still one origin.
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", url=URL)

        assert _url(cache, md5="aaa", endpoint="https://tus.example:443/files/") == URL

    def test_entry_past_the_ttl_is_not_returned(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock, ttl_seconds=100)
        _store(cache, md5="aaa", url=URL)
        clock.now += 101

        assert _url(cache, md5="aaa", endpoint=ENDPOINT) is None

    def test_entry_within_the_ttl_is_returned(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock, ttl_seconds=100)
        _store(cache, md5="aaa", url=URL)
        clock.now += 99

        assert _url(cache, md5="aaa", endpoint=ENDPOINT) == URL

    def test_default_ttl_is_applied(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", url=URL)
        clock.now += DEFAULT_RESUME_TTL_SECONDS + 1

        assert _url(cache, md5="aaa", endpoint=ENDPOINT) is None

    def test_discard_removes_one_entry(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", url=URL)
        _store(cache, md5="bbb", url=URL + "-2")

        cache.discard(md5="aaa")

        assert _url(cache, md5="aaa", endpoint=ENDPOINT) is None
        assert _url(cache, md5="bbb", endpoint=ENDPOINT) == URL + "-2"

    def test_discarding_an_absent_entry_is_a_no_op(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)

        cache.discard(md5="nope")

        assert not cache_path.exists() or json.loads(cache_path.read_text())["entries"] == {}

    def test_expired_entries_are_pruned_on_write(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock, ttl_seconds=100)
        _store(cache, md5="old", url=URL)
        clock.now += 101
        _store(cache, md5="new", url=URL + "-2")

        assert set(json.loads(cache_path.read_text())["entries"]) == {"new"}


class TestTargetScoping:
    """An entry names the records its URL's tus metadata is bound to, and is only reused for them."""

    def test_entry_carries_the_workunit_and_resource(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", workunit_id=109, resource_id=633)

        entry = cache.lookup(md5="aaa", container_id=CONTAINER_ID, application_id=APPLICATION_ID)

        assert (entry.workunit_id, entry.resource_id) == (109, 633)

    def test_a_different_container_is_a_miss(self, cache_path, clock):
        # The same bytes may legitimately be uploaded to another project; adopting the old workunit
        # would file them under the wrong one.
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", container_id=100)

        assert cache.lookup(md5="aaa", container_id=999, application_id=APPLICATION_ID) is None

    def test_a_different_application_is_a_miss(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa")

        assert cache.lookup(md5="aaa", container_id=CONTAINER_ID, application_id=999) is None

    def test_lookup_without_an_endpoint_skips_the_origin_check(self, cache_path, clock):
        # Adoption happens before the tus endpoint is minted, so the origin cannot be compared yet;
        # a cross-origin URL is dropped later, at transfer time.
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa")

        assert cache.lookup(md5="aaa", container_id=CONTAINER_ID, application_id=APPLICATION_ID) is not None

    def test_a_v1_entry_is_ignored(self, cache_path, clock):
        # v1 stored a bare URL with no workunit/resource, so it cannot say what to resume into.
        cache_path.write_text(
            json.dumps({"version": 1, "entries": {"aaa": {"url": URL, "stored_at": clock.now}}}),
        )

        assert ResumeCache(cache_path, now=clock).lookup(md5="aaa", container_id=CONTAINER_ID) is None

    def test_an_entry_missing_its_records_is_ignored(self, cache_path, clock):
        cache_path.write_text(
            json.dumps({"version": 2, "entries": {"aaa": {"url": URL, "stored_at": clock.now}}}),
        )

        assert ResumeCache(cache_path, now=clock).lookup(md5="aaa", container_id=CONTAINER_ID) is None


class TestOnDisk:
    def test_file_is_created_with_owner_only_permissions(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", url=URL)

        assert cache_path.stat().st_mode & 0o777 == 0o600

    def test_parent_directories_are_created(self, tmp_path, clock):
        path = tmp_path / "nested" / "deeper" / "resume.json"
        cache = ResumeCache(path, now=clock)

        _store(cache, md5="aaa", url=URL)

        assert path.exists()

    def test_no_temporary_file_is_left_behind(self, cache_path, clock):
        cache = ResumeCache(cache_path, now=clock)
        _store(cache, md5="aaa", url=URL)

        assert [p.name for p in cache_path.parent.iterdir()] == [cache_path.name]

    def test_a_store_failure_does_not_propagate(self, mocker, cache_path, clock):
        # The cache is an optimisation: losing it must never fail a transfer that is going fine.
        cache = ResumeCache(cache_path, now=clock)
        mocker.patch("bfabric.transfer.resume_cache.os.open", side_effect=OSError("read-only fs"))

        _store(cache, md5="aaa", url=URL)

        assert _url(cache, md5="aaa", endpoint=ENDPOINT) is None
