from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from freezegun import freeze_time
from inline_snapshot import snapshot
from pytest_mock import MockerFixture

from bfabric.results.result_container import ResultContainer
from bfabric_scripts.bfabric_list_not_existing_storage_directories import (
    list_not_existing_storage_dirs,
)


@freeze_time("2025-07-25")
def test_list_not_existing_storage_directories(
    capfd: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    # create a few directories
    existing = [tmp_path / d for d in ["p3000", "p3100", "p3200"]]
    for path in existing:
        path.mkdir()

    # mock a client
    client = mocker.MagicMock()
    client.read.return_value = ResultContainer(
        [{"id": 3000}, {"id": 3050}, {"id": 3100}, {"id": 3200}, {"id": 3300}], total_pages_api=None, errors=[]
    )

    # call the function
    list_not_existing_storage_dirs(root_dir=tmp_path, client=client)

    # check output
    out, err = capfd.readouterr()
    assert err == snapshot(
        """\
INFO Checking containers modified after cutoff date: 2025-07-11
INFO Found 2 containers with not existing storage directories.
"""
    )
    # assert err == ""
    assert out == "3050\n3300\n"

    client.read.assert_called_once_with(
        endpoint="container",
        obj={"technologyid": [2, 4], "modifiedafter": "2025-07-11"},
        return_id_only=True,
        max_results=None,
    )


if __name__ == "__main__":
    pytest.main()
