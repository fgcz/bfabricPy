from pathlib import Path

from bfabric.experimental.workunit_definition import WorkunitDefinition, WorkunitExecutionDefinition


def test_workunit_definition_from_workunit(mocker):
    workunit = mocker.Mock(
        application=mocker.MagicMock(id=1, __getitem__=lambda self, k: {"name": "application (mocked)"}[k]),
        id=2,
        __getitem__=lambda self, k: {"name": "workunit (mocked)"}[k],
        input_dataset=None,
        input_resources=[mocker.Mock(id=3), mocker.Mock(id=4)],
        application_parameters={"param1": "value1", "param2": "value2"},
        container=mocker.Mock(id=5, ENDPOINT="project"),
        store_output_folder="output_folder",
    )
    workunit_definition = WorkunitDefinition.from_workunit(workunit)
    assert workunit_definition.execution.raw_parameters == {"param1": "value1", "param2": "value2"}
    assert workunit_definition.execution.dataset is None
    assert workunit_definition.execution.resources == [3, 4]
    assert workunit_definition.registration.application_id == 1
    assert workunit_definition.registration.application_name == "application_mocked_"
    assert workunit_definition.registration.workunit_id == 2
    assert workunit_definition.registration.workunit_name == "workunit_mocked_"
    assert workunit_definition.registration.container_id == 5
    assert workunit_definition.registration.container_type == "project"
    assert workunit_definition.registration.storage_id == 1
    assert workunit_definition.registration.storage_output_folder == Path("output_folder")
