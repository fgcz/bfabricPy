from unittest.mock import Mock

import pytest

from bfabric_app_runner.bfabric_integration.submitter.config.slurm_params import (
    _SlurmConfigFileTemplate,
    SlurmParameters,
)
from bfabric_app_runner.bfabric_integration.submitter.config.slurm_workunit_params import SlurmWorkunitParams
from bfabric_app_runner.specs.config_interpolation import VariablesApp, VariablesWorkunit


@pytest.fixture
def slurm_config_file_template():
    return _SlurmConfigFileTemplate(
        params={"--partition": "test", "--nodes": 1, "--name": "workunit-${workunit.id}"},
        job_script="/home/test/test/job-${workunit.id}",
    )


@pytest.fixture
def variables_app():
    return VariablesApp(id=1, name="test_app", version="1.0.0")


@pytest.fixture
def variables_workunit():
    return VariablesWorkunit(id=42)


def test_slurm_config_template_evaluation(slurm_config_file_template, variables_app, variables_workunit):
    """Test that template evaluation correctly interpolates variables."""
    # Evaluate the template
    config_file = slurm_config_file_template.evaluate(variables_app, variables_workunit)

    # Verify interpolation worked
    assert config_file.params["--name"] == "workunit-42"
    assert config_file.params["--partition"] == "test"
    assert config_file.params["--nodes"] == 1
    assert str(config_file.job_script) == "/home/test/test/job-42"


def test_slurm_parameters_creation():
    """Test SlurmParameters creation and sbatch_params merging."""
    # Mock workunit params
    mock_workunit_params = Mock(spec=SlurmWorkunitParams)
    mock_workunit_params.as_dict.return_value = {"--time": "01:00:00", "--mem": "4G"}

    # Create SlurmParameters
    slurm_params = SlurmParameters(
        submitter_params={"--partition": "compute", "--nodes": 2, "--name": "test-job"},
        job_script="/path/to/job.sh",
        workunit_params=mock_workunit_params,
    )

    # Test sbatch_params merging
    sbatch_params = slurm_params.sbatch_params
    assert sbatch_params["--partition"] == "compute"
    assert sbatch_params["--nodes"] == "2"
    assert sbatch_params["--name"] == "test-job"
    assert sbatch_params["--time"] == "01:00:00"
    assert sbatch_params["--mem"] == "4G"

    # Verify all values are strings
    for value in sbatch_params.values():
        assert isinstance(value, str)


def test_template_with_app_variables():
    """Test template evaluation with app variables."""
    template = _SlurmConfigFileTemplate(
        params={"--job-name": "${app.name}-${workunit.id}"}, job_script="/home/${app.name}/job-${workunit.id}"
    )

    app = VariablesApp(id=1, name="my_app", version="1.0.0")
    workunit = VariablesWorkunit(id=123)

    result = template.evaluate(app, workunit)

    assert result.params["--job-name"] == "my_app-123"
    assert str(result.job_script) == "/home/my_app/job-123"
