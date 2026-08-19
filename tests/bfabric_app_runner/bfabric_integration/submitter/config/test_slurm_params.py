from pathlib import Path

import pytest

from bfabric_app_runner.bfabric_integration.submitter.config.slurm_params import (
    _evaluate_app_params,
    _SlurmConfigFileTemplate,
    SlurmParameters,
)
from bfabric_app_runner.bfabric_integration.submitter.config.slurm_workunit_params import SlurmWorkunitParams
from bfabric_app_runner.specs.config_interpolation import VariablesApp, VariablesWorkunit


@pytest.fixture
def slurm_config_file_template():
    return _SlurmConfigFileTemplate(
        params={"--partition": "test", "--nodes": 1, "--name": "workunit-${workunit.id}"},
        job_script="~/test/job-${workunit.id}",
        scratch_root="/scratch",
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
    assert config_file.job_script == Path("~/test/job-42").expanduser()


def test_slurm_config_template_for_yaml(tmp_path, variables_app, variables_workunit):
    """The documented submitter.yml shape parses off disk, including templating and a `~` path."""
    path = tmp_path / "submitter.yml"
    path.write_text(
        "params:\n"
        "  --partition: prx\n"
        "  --mem: 256G\n"
        "  --job-name: WU${workunit.id}\n"
        "job_script: ~/prx/workunitid-${workunit.id}.bash\n"
        "scratch_root: /scratch\n"
    )
    config_file = _SlurmConfigFileTemplate.for_yaml(path).evaluate(variables_app, variables_workunit)
    assert config_file.params == {"--partition": "prx", "--mem": "256G", "--job-name": "WU42"}
    assert config_file.job_script == Path("~/prx/workunitid-42.bash").expanduser()
    assert config_file.scratch_root == Path("/scratch")


def test_slurm_parameters_creation(mocker):
    """Test SlurmParameters creation and sbatch_params merging."""
    # Mock workunit params
    mock_workunit_params = mocker.Mock(spec=SlurmWorkunitParams)
    mock_workunit_params.as_dict.return_value = {"--time": "01:00:00", "--mem": "4G"}

    # Create SlurmParameters
    slurm_params = SlurmParameters(
        submitter_params={"--partition": "compute", "--nodes": 2, "--name": "test-job"},
        job_script="/path/to/job.sh",
        workunit_params=mock_workunit_params,
        scratch_root="/scratch",
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


class TestSbatchParamsPrecedence:
    """The three parameter sources merge as submitter.yml < app.yml < workunit."""

    @staticmethod
    def _params(submitter_params, app_params, workunit_params) -> SlurmParameters:
        return SlurmParameters(
            submitter_params=submitter_params,
            app_params=app_params,
            job_script="/path/to/job.sh",
            workunit_params=SlurmWorkunitParams.model_validate(workunit_params),
            scratch_root="/scratch",
        )

    def test_app_overrides_submitter(self):
        params = self._params({"--mem": "256G"}, {"--mem": "512G"}, {})
        assert params.sbatch_params["--mem"] == "512G"

    def test_workunit_overrides_app(self):
        params = self._params({"--mem": "256G"}, {"--mem": "512G"}, {"--mem": "960G"})
        assert params.sbatch_params["--mem"] == "960G"

    def test_app_params_add_new_flags(self):
        params = self._params({"--mem": "256G"}, {"--cpus-per-task": 24}, {})
        assert params.sbatch_params == {"--mem": "256G", "--cpus-per-task": "24"}

    def test_app_null_drops_submitter_default(self):
        params = self._params({"--nodelist": "fgcz-r-024"}, {"--nodelist": None}, {})
        assert "--nodelist" not in params.sbatch_params

    def test_app_params_default_to_empty(self):
        params = SlurmParameters(
            submitter_params={"--mem": "256G"},
            job_script="/path/to/job.sh",
            workunit_params=SlurmWorkunitParams(),
            scratch_root="/scratch",
        )
        assert params.sbatch_params == {"--mem": "256G"}


class TestEvaluateAppParams:
    """Reading ``slurm_params`` out of the app.yml must never block a submission."""

    @pytest.fixture()
    def app_yaml(self, tmp_path) -> Path:
        path = tmp_path / "app.yml"
        path.write_text(
            "bfabric:\n"
            "  app_runner: 0.7.0\n"
            "versions:\n"
            "  - version: '1.0.0'\n"
            "    commands:\n"
            "      dispatch: {type: shell, command: d}\n"
            "      process: {type: shell, command: p}\n"
            "    slurm_params:\n"
            "      --cpus-per-task: 24\n"
        )
        return path

    @pytest.fixture()
    def workunit(self, mocker, app_yaml):
        workunit = mocker.MagicMock(name="workunit")
        workunit.id = 42
        workunit.application.id = 1000
        workunit.application.__getitem__.side_effect = {"name": "MyApp"}.__getitem__
        workunit.application.executable.__getitem__.side_effect = {"program": str(app_yaml)}.__getitem__
        workunit.application_parameters = {"application_version": "1.0.0"}
        return workunit

    def test_returns_params_of_resolved_version(self, workunit):
        assert _evaluate_app_params(workunit) == {"--cpus-per-task": 24}

    def test_missing_app_yaml_returns_empty(self, workunit, tmp_path):
        workunit.application.executable.__getitem__.side_effect = {"program": str(tmp_path / "nope.yml")}.__getitem__
        assert _evaluate_app_params(workunit) == {}

    def test_unparseable_app_yaml_returns_empty(self, workunit, app_yaml):
        app_yaml.write_text("versions: [{oops")
        assert _evaluate_app_params(workunit) == {}

    def test_unknown_version_returns_empty(self, workunit):
        workunit.application_parameters = {"application_version": "9.9.9"}
        assert _evaluate_app_params(workunit) == {}

    def test_absent_version_parameter_uses_the_only_version(self, workunit):
        """An app that never had an ``application_version`` parameter still gets its params."""
        workunit.application_parameters = {}
        assert _evaluate_app_params(workunit) == {"--cpus-per-task": 24}

    def test_absent_version_parameter_returns_empty_when_several_versions_exist(self, workunit, app_yaml):
        app_yaml.write_text(app_yaml.read_text().replace("  - version: '1.0.0'\n", "  - version: ['1.0.0', '1.0.1']\n"))
        workunit.application_parameters = {}
        assert _evaluate_app_params(workunit) == {}

    def test_a_submitter_defect_is_not_swallowed(self, workunit):
        """Only reading the spec is fail-safe; a bug on our side must not cost the app its params silently."""
        workunit.application_parameters = None
        with pytest.raises(AttributeError):
            _evaluate_app_params(workunit)


def test_template_with_app_variables():
    """Test template evaluation with app variables."""
    template = _SlurmConfigFileTemplate(
        params={"--job-name": "${app.name}-${workunit.id}"},
        job_script="/home/${app.name}/job-${workunit.id}",
        scratch_root="/scratch",
    )

    app = VariablesApp(id=1, name="my_app", version="1.0.0")
    workunit = VariablesWorkunit(id=123)

    result = template.evaluate(app, workunit)

    assert result.params["--job-name"] == "my_app-123"
    assert str(result.job_script) == "/home/my_app/job-123"
