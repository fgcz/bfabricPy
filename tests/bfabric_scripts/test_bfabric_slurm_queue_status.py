import polars as pl
import polars.testing
import pytest

from bfabric.entities import Workunit, Application
from bfabric_scripts.bfabric_slurm_queue_status import (
    get_slurm_jobs,
    get_workunit_infos,
)


@pytest.fixture
def command_output():
    return (
        "JOBID\tNAME\tNODELIST\n"
        "1234\tWU5000\tserver-01\n"
        "5678\tWU5001\tserver-02\n"
        "9999\tsomething else\tserver-01\n"
    )


def test_get_slurm_jobs_when_local(mocker, command_output):
    mocker.patch("subprocess.run", return_value=mocker.Mock(stdout=command_output))
    df = get_slurm_jobs("mypartition", None)

    expected_df = pl.DataFrame(
        [
            [1234, "WU5000", "server-01", 5000],
            [5678, "WU5001", "server-02", 5001],
            [9999, "something else", "server-01", None],
        ],
        schema=["job_id", "name", "node_list", "workunit_id"],
        orient="row",
    )
    pl.testing.assert_frame_equal(df, expected_df)


def test_get_workunit_infos(mocker):
    mock_client = mocker.Mock(name="mock_client")
    mock_workunit_find_all = mocker.patch.object(Workunit, "find_all")
    workunit_ids = [5000, 5001]
    mock_workunit_find_all.return_value = {
        5001: Workunit({"id": 5000, "status": "RUNNING", "application": {"id": 1}}),
    }
    mock_app_find_all = mocker.patch.object(Application, "find_all")
    mock_app_find_all.return_value = {1: {"id": 1, "name": "myapp"}}
    infos = get_workunit_infos(mock_client, workunit_ids)
    assert infos == [
        {"workunit_id": 5000, "status": "ZOMBIE", "application_name": "N/A"},
        {"workunit_id": 5001, "status": "RUNNING", "application_name": "myapp"},
    ]
    mock_workunit_find_all.assert_called_once_with(ids=workunit_ids, client=mock_client)


if __name__ == "__main__":
    pytest.main()
