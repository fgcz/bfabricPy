from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from bfabric.results.result_container import ResultContainer
from bfabric.scripts.bfabric_list_not_existing_storage_directories import list_not_existing_storage_dirs


def test_list_not_existing_storage_directories(
    capfd: pytest.CaptureFixture[str], mocker: MockerFixture, tmp_path: Path
) -> None:
    # create a few directories
    existing = [tmp_path / d for d in ["p3000", "p3100", "p3200"]]
    for path in existing:
        path.mkdir()

    # mock a client
    client = mocker.MagicMock()
    client.read.return_value = ResultContainer([{"id": 3000}, {"id": 3050}, {"id": 3100}, {"id": 3200}, {"id": 3300}])

    # call the function
    list_not_existing_storage_dirs(client, tmp_path, cache_path=tmp_path / "cache.json")

    # check output
    out, err = capfd.readouterr()
    assert err == ""
    assert out == "3050\n3300\n"

    client.read.assert_called_once_with(
        endpoint="container",
        obj={"technologyid": [2, 4], "createdafter": "2023-12-31T00:00:00"},
        return_id_only=True,
        max_results=None,
    )


if __name__ == "__main__":
    pytest.main()
