from pathlib import Path, PosixPath

import pytest
import yaml

from bfabric.experimental.workunit_definition import (
    WorkunitDefinition,
    WorkunitExecutionDefinition,
    WorkunitRegistrationDefinition,
)
from bfabric_app_runner.app_runner.resolve_app import load_workunit_information
from bfabric_app_runner.specs.app.app_spec import AppSpec, BfabricAppSpec
from bfabric_app_runner.specs.app.app_version import AppVersion
from bfabric_app_runner.specs.app.commands_spec import CommandsSpec, CommandExec


class TestLoadWorkunitInformation:
    @pytest.fixture
    def app_spec(self):
        return AppSpec(
            bfabric=BfabricAppSpec(app_runner="0.1.0"),
            versions=[
                AppVersion(
                    version="xyz",
                    commands=CommandsSpec(
                        dispatch=CommandExec(
                            command="bash -c 'echo dispatching'",
                        ),
                        process=CommandExec(
                            command="bash -c 'echo processing'",
                        ),
                    ),
                )
            ],
        )

    @pytest.fixture
    def app_spec_yaml(self, app_spec) -> str:
        return yaml.safe_dump(app_spec.model_dump(mode="json"))

    @pytest.fixture
    def app_spec_path(self, fs, app_spec_yaml):
        path = Path("/fake/work/app_spec.yml")
        fs.create_file(path, contents=app_spec_yaml)
        return path

    @pytest.fixture
    def workunit_definition(self):
        return WorkunitDefinition(
            execution=WorkunitExecutionDefinition(
                raw_parameters={"hello": "world", "application_version": "xyz"},
                dataset=1234,
            ),
            registration=WorkunitRegistrationDefinition(
                application_id=1,
                application_name="test_app",
                workunit_id=2,
                workunit_name="test_workunit",
                container_id=3,
                container_type="project",
                storage_id=4,
                storage_output_folder=PosixPath("/fake/remote/path"),
            ),
        )

    @pytest.fixture
    def workunit_definition_yaml(self, workunit_definition) -> str:
        return yaml.safe_dump(workunit_definition.model_dump(mode="json"))

    @pytest.fixture
    def workunit_definition_path(self, fs, workunit_definition_yaml) -> Path:
        path = Path("/fake/work/workunit_definition.yml")
        fs.create_file(path, contents=workunit_definition_yaml)
        return path

    def test_from_path(self, mocker, app_spec_path, workunit_definition_path, app_spec, workunit_definition):
        mock_client = mocker.Mock(name="mock_client")
        mocker.patch(
            "bfabric_app_runner.app_runner.resolve_app._resolve_workunit_definition",
            return_value=(workunit_definition, workunit_definition_path),
        )

        return_app_version, return_bfabric_app_spec, return_workunit_ref = load_workunit_information(
            app_spec=app_spec_path,
            client=mock_client,
            work_dir=Path("/fake/work"),
            workunit_ref=workunit_definition_path,
        )

        assert return_app_version == app_spec.versions[0]
        assert return_bfabric_app_spec == app_spec.bfabric
        assert return_workunit_ref == workunit_definition_path
