import pytest
import yaml
from pydantic import ValidationError

from bfabric_app_runner.specs.app.app_version import AppVersion, AppVersionMultiTemplate, AppVersionTemplate
from bfabric_app_runner.specs.app.commands_spec import (
    CommandShell,
    CommandDocker,
    MountOptions,
    CommandsSpec,
)
from bfabric_app_runner.specs.config_interpolation import VariablesApp


@pytest.fixture()
def parsed() -> AppVersion:
    return AppVersion(
        version="0.0.1",
        commands=CommandsSpec(
            dispatch=CommandShell(command="dispatch"),
            process=CommandDocker(
                image="image",
                command="command",
                mounts=MountOptions(read_only=[("/host", "/container")]),
            ),
            collect=CommandShell(command="collect"),
        ),
        reuse_default_resource=True,
    )


@pytest.fixture()
def serialized() -> str:
    return """commands:
  collect:
    command: collect
    type: shell
  dispatch:
    command: dispatch
    type: shell
  process:
    command: command
    custom_args: []
    engine: docker
    entrypoint: null
    env: {}
    hostname: null
    image: image
    mac_address: null
    mounts:
      read_only:
      - - /host
        - /container
      share_bfabric_config: true
      work_dir_target: null
      writeable: []
    type: docker
reuse_default_resource: true
submitter_params: {}
version: 0.0.1"""


def test_serialize(parsed, serialized):
    assert yaml.safe_dump(parsed.model_dump(mode="json")).strip() == serialized.strip()


def test_parse(parsed, serialized):
    assert AppVersion.model_validate(yaml.safe_load(serialized)) == parsed


class TestSubmitterParams:
    @staticmethod
    def _app_version(submitter_params) -> AppVersion:
        return AppVersion(
            version="1.0.0",
            commands=CommandsSpec(dispatch=CommandShell(command="d"), process=CommandShell(command="p")),
            submitter_params=submitter_params,
        )

    def test_defaults_to_empty(self, parsed):
        assert parsed.submitter_params == {}

    def test_accepts_str_and_int_values(self):
        app_version = self._app_version({"--cpus-per-task": 24, "--mem": "512G"})
        assert app_version.submitter_params == {"--cpus-per-task": 24, "--mem": "512G"}

    def test_accepts_null_to_drop_a_flag(self):
        assert self._app_version({"--nodelist": None}).submitter_params == {"--nodelist": None}

    def test_rejects_key_without_double_dash(self):
        with pytest.raises(ValidationError, match="String should match pattern"):
            self._app_version({"cpus-per-task": 24})

    def test_rejects_key_with_equals_sign(self):
        with pytest.raises(ValidationError, match="must not contain"):
            self._app_version({"--mem=512G": None})

    def test_rejects_reserved_flag(self):
        with pytest.raises(ValidationError, match="reserved by the submitter"):
            self._app_version({"--output": "/tmp/my.log"})

    def test_rejects_workunit_variable(self):
        with pytest.raises(ValidationError, match=r"\$\{workunit"):
            self._app_version({"--comment": "wu-${workunit.id}"})

    def test_interpolates_app_variables(self):
        template = AppVersionTemplate(
            version="1.0.0",
            commands=CommandsSpec(dispatch=CommandShell(command="d"), process=CommandShell(command="p")),
            submitter_params={"--comment": "app-${app.id}", "--cpus-per-task": 24},
        )
        app_version = template.evaluate(variables_app=VariablesApp(id=7, name="x", version="1.0.0"))
        assert app_version.submitter_params == {"--comment": "app-7", "--cpus-per-task": 24}

    def test_expand_versions_carries_params(self):
        multi = AppVersionMultiTemplate(
            version=["1.0.0", "1.0.1"],
            commands=CommandsSpec(dispatch=CommandShell(command="d"), process=CommandShell(command="p")),
            submitter_params={"--mem": "512G"},
        )
        assert [template.submitter_params for template in multi.expand_versions()] == [{"--mem": "512G"}] * 2
