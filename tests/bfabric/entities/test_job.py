from __future__ import annotations

from bfabric.entities import Job


def test_endpoint() -> None:
    assert Job.ENDPOINT == "job"


def test_construct(mock_client, bfabric_instance) -> None:
    job = Job({"id": 1}, client=mock_client, bfabric_instance=bfabric_instance)
    assert job.id == 1
