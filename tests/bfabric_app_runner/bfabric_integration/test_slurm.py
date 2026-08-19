from pathlib import Path

import pytest
from inline_snapshot import snapshot

from bfabric_app_runner.bfabric_integration.slurm import _submit_workunit

SUBMITTER_YAML = """
params:
  --nodes: 1
  --cpus-per-task: 1
  --partition: prx
  --mem: 256G
  --job-name: WU${workunit.id}
  --output: LOG_DIR/workunitid-${workunit.id}.log
job_script: JOB_DIR/workunitid-${workunit.id}.bash
scratch_root: /scratch
"""

APP_YAML = """
bfabric:
  app_runner: 0.7.0
versions:
  - version: '1.0.0'
    commands:
      dispatch: {type: shell, command: d}
      process: {type: shell, command: p}
"""


@pytest.fixture()
def app_yaml(tmp_path) -> Path:
    path = tmp_path / "app.yml"
    path.write_text(APP_YAML)
    return path


@pytest.fixture()
def submitter_yaml(tmp_path) -> Path:
    path = tmp_path / "submitter.yml"
    path.write_text(SUBMITTER_YAML.replace("LOG_DIR", str(tmp_path / "log")).replace("JOB_DIR", str(tmp_path / "jobs")))
    return path


@pytest.fixture()
def workunit(mocker, app_yaml):
    workunit = mocker.MagicMock(name="workunit")
    workunit.id = 42
    workunit.application.id = 1000
    workunit.application.__getitem__.side_effect = {"name": "MyApp"}.__getitem__
    workunit.application.executable.__getitem__.side_effect = {"program": str(app_yaml)}.__getitem__
    workunit.application_parameters = {"application_version": "1.0.0"}
    workunit.submitter_parameters = {}
    return workunit


@pytest.fixture()
def run(mocker):
    return mocker.patch("bfabric_app_runner.bfabric_integration.slurm.subprocess.run")


def _submitted_script(tmp_path: Path) -> str:
    return (tmp_path / "jobs" / "workunitid-42.bash").read_text()


class TestSubmitWorkunit:
    def test_renders_the_expected_job_script(self, workunit, submitter_yaml, tmp_path, run, app_yaml):
        """Golden render: covers both mako templates and the sbatch parameter merge at once."""
        _submit_workunit(workunit=workunit, config_path=submitter_yaml)
        script = _submitted_script(tmp_path).replace(str(app_yaml), "APP_YAML").replace(str(tmp_path), "TMP")
        assert script == snapshot(
            """\
#!/bin/bash
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=prx
#SBATCH --mem=256G
#SBATCH --job-name=WU42
#SBATCH --output=TMP/log/workunitid-42.log
set -euo pipefail
{
set -x
id
hostname
export PYTHONUNBUFFERED=1
export BFABRICPY_CONFIG_ENV=$BFABRICPY_CONFIG_ENV
export XDG_CACHE_HOME=$XDG_CACHE_HOME
# shellcheck disable=SC2016,SC2154
# Determine app runner version
get_app_runner_version() {
    uv run -p 3.13 --with "pyyaml==6.0.2" python - "$1" <<'EOF'
import yaml
import sys
import re
from pathlib import Path
yaml_path = Path(sys.argv[1])
version_string = yaml.safe_load(yaml_path.read_text())["bfabric"]["app_runner"]
if re.match(r"^\\d+\\.\\d+\\.\\d+$", version_string):
    print(f"bfabric-app-runner=={version_string}")
else:
    print(f"bfabric-app-runner@{version_string}")
EOF
}
app_runner_version=$(get_app_runner_version "APP_YAML")

# Run
uv run -p 3.13 --with "$app_runner_version" bfabric-app-runner     run workunit --app-definition 'APP_YAML' --scratch-root '/scratch' --workunit-ref '42'

} 2>&1 | while read line; do echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"; done
"""
        )

    def test_submits_the_written_script(self, workunit, submitter_yaml, tmp_path, run):
        _submit_workunit(workunit=workunit, config_path=submitter_yaml)
        run.assert_called_once_with(["sbatch", str(tmp_path / "jobs" / "workunitid-42.bash")], check=True)

    def test_creates_the_log_directory(self, workunit, submitter_yaml, tmp_path, run):
        _submit_workunit(workunit=workunit, config_path=submitter_yaml)
        assert (tmp_path / "log").is_dir()

    def test_app_slurm_params_reach_the_script(self, workunit, submitter_yaml, tmp_path, run, app_yaml):
        app_yaml.write_text(APP_YAML + "    slurm_params:\n      --cpus-per-task: 24\n      --licenses: sn:1\n")
        _submit_workunit(workunit=workunit, config_path=submitter_yaml)
        script = _submitted_script(tmp_path)
        assert "#SBATCH --cpus-per-task=24" in script
        assert "#SBATCH --licenses=sn:1" in script

    def test_workunit_parameters_win_over_the_app(self, workunit, submitter_yaml, tmp_path, run, app_yaml):
        app_yaml.write_text(APP_YAML + "    slurm_params:\n      --mem: 512G\n")
        workunit.submitter_parameters = {"--mem": "960G"}
        _submit_workunit(workunit=workunit, config_path=submitter_yaml)
        assert "#SBATCH --mem=960G" in _submitted_script(tmp_path)

    def test_a_compat_wrapper_program_is_refused_before_anything_happens(
        self, workunit, submitter_yaml, tmp_path, run, app_yaml
    ):
        """The guard must fire before the job script is written and before sbatch is called."""
        workunit.application.executable.__getitem__.side_effect = {
            "program": f"/opt/compat.bash {app_yaml}"
        }.__getitem__
        with pytest.raises(ValueError, match="not a single path"):
            _submit_workunit(workunit=workunit, config_path=submitter_yaml)
        assert not (tmp_path / "jobs").exists()
        run.assert_not_called()
