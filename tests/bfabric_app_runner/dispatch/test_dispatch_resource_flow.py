from pathlib import Path
from typing import Any

import polars as pl
import polars.testing
import pytest
import yaml

from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_app_runner.dispatch.dispatch_resource_flow import (
    ResourceDispatcher,
)


@pytest.fixture
def mock_bfabric(mocker):
    return mocker.Mock(spec=Bfabric)


@pytest.fixture
def mock_workunit_definition(mocker):
    mock_def = mocker.Mock(spec=WorkunitDefinition, execution=mocker.Mock())
    mock_def.execution.resources = [1, 2, 3]  # Sample resource IDs
    return mock_def


@pytest.fixture
def sample_resources():
    return {
        1: {"id": 1, "relativepath": "path/to/file1.txt"},
        2: {"id": 2, "relativepath": "path/to/file2.txt"},
        3: {"id": 3, "relativepath": "path/to/file3.txt"},
    }


@pytest.fixture
def mock_resource_find_all(mocker, sample_resources):
    mocker.patch.object(Resource, "find_all", return_value=sample_resources)


@pytest.fixture
def sample_input_df():
    data = {
        "resource_id": [1, 2, 3],
        "filename": ["file1.txt", "file2.txt", "file3.txt"],
        "relativepath": ["path/to/file1.txt", "path/to/file2.txt", "path/to/file3.txt"],
    }
    return pl.DataFrame(data)


@pytest.fixture
def sample_output_df():
    """Fixture for sample output DataFrame."""
    data = {
        "resource_id": [1, 2],
        "filename": ["file1.txt", "file2.txt"],
        "task": ["work", "work"],
    }
    return pl.DataFrame(data)


@pytest.fixture
def mock_resource_strategy():
    class MockStrategy:
        def __call__(self, resources_df: Any, workunit_definition: WorkunitDefinition) -> Any:
            # Return sample output DataFrame
            return pl.DataFrame(
                {
                    "resource_id": [1, 2],
                    "filename": ["file1.txt", "file2.txt"],
                    "task": ["work", "work"],
                }
            )

    return MockStrategy()


@pytest.fixture
def resource_dispatcher():
    return ResourceDispatcher()


def test_build_input_resources_df(resource_dispatcher, mock_bfabric, mock_resource_find_all, sample_resources):
    result = resource_dispatcher._build_input_resources_df([1, 2, 3], mock_bfabric)
    expected = pl.DataFrame(
        [
            {"resource_id": 1, "filename": "file1.txt", "relativepath": "path/to/file1.txt"},
            {"resource_id": 2, "filename": "file2.txt", "relativepath": "path/to/file2.txt"},
            {"resource_id": 3, "filename": "file3.txt", "relativepath": "path/to/file3.txt"},
        ]
    )
    pl.testing.assert_frame_equal(result, expected)


def test_build_input_resources_df_when_empty(resource_dispatcher, mock_bfabric, mocker):
    mocker.patch.object(Resource, "find_all", return_value={})
    with pytest.raises(ValueError, match="No resources to dispatch"):
        resource_dispatcher._build_input_resources_df([1, 2, 3], mock_bfabric)


def test_build_inputs_spec(resource_dispatcher, sample_output_df):
    result = resource_dispatcher._build_inputs_spec(sample_output_df)
    expected = {
        "inputs": [
            {"type": "bfabric_resource", "id": 1, "filename": "file1.txt"},
            {"type": "bfabric_resource", "id": 2, "filename": "file2.txt"},
        ]
    }
    assert result == expected


def test_evaluate_strategy(resource_dispatcher, mock_resource_strategy, sample_input_df, mock_workunit_definition):
    result, extra_inputs = resource_dispatcher._evaluate_strategy(
        sample_input_df, mock_workunit_definition, mock_resource_strategy
    )
    expected_result = pl.DataFrame(
        [
            {"resource_id": 1, "filename": "file1.txt", "task": "work"},
            {"resource_id": 2, "filename": "file2.txt", "task": "work"},
        ]
    )
    pl.testing.assert_frame_equal(result, expected_result)
    assert extra_inputs == []


def test_evaluate_strategy_with_extra_inputs(resource_dispatcher, sample_input_df, mock_workunit_definition):
    extra_inputs = [{"type": "extra", "id": 4, "filename": "extra.txt"}]

    class StrategyWithExtras:
        def __call__(self, resources_df, workunit_definition):
            return (
                pl.DataFrame(
                    {
                        "resource_id": [1],
                        "filename": ["file1.txt"],
                        "task": ["work"],
                    }
                ),
                extra_inputs,
            )

    result, returned_extra_inputs = resource_dispatcher._evaluate_strategy(
        sample_input_df, mock_workunit_definition, StrategyWithExtras()
    )

    expected_result = pl.DataFrame([{"resource_id": 1, "filename": "file1.txt", "task": "work"}])
    pl.testing.assert_frame_equal(result, expected_result)
    assert returned_extra_inputs == extra_inputs


def test_dispatch(
    resource_dispatcher,
    mock_bfabric,
    mock_workunit_definition,
    mock_resource_strategy,
    mock_resource_find_all,
    fs,
):
    """Test the dispatch method with fake filesystem."""
    work_dir = Path("/tmp/work")
    fs.create_dir(work_dir)

    resource_dispatcher.dispatch(mock_workunit_definition, work_dir, mock_resource_strategy, client=mock_bfabric)

    # Check if directories and files were created
    assert (work_dir / "work").exists()
    assert (work_dir / "chunks.yml").exists()

    # Verify chunks.yml content
    with (work_dir / "chunks.yml").open("r") as f:
        chunks_content = yaml.safe_load(f)
        assert chunks_content == {"chunks": ["work"]}

    # Verify work directory contains inputs.yml
    work_inputs_path = work_dir / "work" / "inputs.yml"
    assert work_inputs_path.exists()
    with work_inputs_path.open("r") as f:
        inputs_content = yaml.safe_load(f)
        assert inputs_content == {
            "inputs": [
                {"type": "bfabric_resource", "id": 1, "filename": "file1.txt"},
                {"type": "bfabric_resource", "id": 2, "filename": "file2.txt"},
            ]
        }


def test_create_task_dir(
    resource_dispatcher,
    sample_output_df,
    fs,
):
    """Test _create_task_dir method with fake filesystem."""
    work_dir = Path("/tmp/work")
    fs.create_dir(work_dir)

    extra_inputs = [{"type": "extra", "id": 4, "filename": "extra.txt"}]

    resource_dispatcher._create_task_dir(
        extra_inputs=extra_inputs, requested_table=sample_output_df, task="work", work_dir=work_dir
    )

    # Check if task directory and file were created
    task_dir = work_dir / "work"
    inputs_file = task_dir / "inputs.yml"
    assert task_dir.exists()
    assert inputs_file.exists()

    # Verify inputs.yml content
    with inputs_file.open("r") as f:
        inputs_content = yaml.safe_load(f)
        expected_inputs = {
            "inputs": [
                {"type": "bfabric_resource", "id": 1, "filename": "file1.txt"},
                {"type": "bfabric_resource", "id": 2, "filename": "file2.txt"},
                {"type": "extra", "id": 4, "filename": "extra.txt"},
            ]
        }
        assert inputs_content == expected_inputs


def test_determine_requested_inputs(
    resource_dispatcher, mock_bfabric, mock_workunit_definition, mock_resource_strategy, mock_resource_find_all
):
    """Test _determine_requested_inputs method with more specific assertions."""
    extra_inputs, requested_table, tasks = resource_dispatcher._determine_requested_inputs(
        client=mock_bfabric, resource_strategy=mock_resource_strategy, workunit_definition=mock_workunit_definition
    )

    # Check extra_inputs
    assert extra_inputs == []

    # Check requested_table structure and content
    expected_table = pl.DataFrame(
        {
            "resource_id": [1, 2],
            "filename": ["file1.txt", "file2.txt"],
            "task": ["work", "work"],
        }
    )
    pl.testing.assert_frame_equal(requested_table, expected_table)

    # Check tasks
    assert tasks == ["work"]
