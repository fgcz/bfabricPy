import polars as pl
import polars.testing
import pytest

from bfabric.entities import Workunit, Application
from bfabric.entities.core.entity_reader import EntityResult
from bfabric.entities.core.uri import EntityUri
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
    instance = "https://example.com/bfabric/"
    workunit_ids = [5000, 5001]

    # `get_workunit_infos` calls `client.reader.read_ids` for the Workunit and Application types and
    # reshapes the results with the `.by_id` (keyed by URI id) and `.present` views of EntityResult. The
    # URI id (5001) deliberately differs from the workunit's own data id (5000) to pin down which one is used.
    workunit_result = EntityResult(
        {
            EntityUri.from_components(instance, "workunit", 5001): Workunit(
                {"id": 5000, "status": "RUNNING", "application": {"id": 1}}, bfabric_instance=instance
            ),
        }
    )
    application_result = EntityResult(
        {
            EntityUri.from_components(instance, "application", 1): {"id": 1, "name": "myapp"},
        }
    )

    def fake_read_ids(entity_type, ids, *args, **kwargs):
        if entity_type is Workunit:
            return workunit_result
        if entity_type is Application:
            return application_result
        raise AssertionError(f"unexpected entity type: {entity_type!r}")

    mock_client.reader.read_ids.side_effect = fake_read_ids

    infos = get_workunit_infos(mock_client, workunit_ids)
    assert infos == [
        {"workunit_id": 5000, "status": "ZOMBIE", "application_name": "N/A"},
        {"workunit_id": 5001, "status": "RUNNING", "application_name": "myapp"},
    ]
    mock_client.reader.read_ids.assert_any_call(Workunit, workunit_ids)
    mock_client.reader.read_ids.assert_any_call(Application, [1])


if __name__ == "__main__":
    pytest.main()
