import importlib.resources
from pathlib import Path

import pytest
import yaml

from bfabric.experimental.workunit_definition import (
    WorkunitDefinition,
    WorkunitExecutionDefinition,
    WorkunitRegistrationDefinition,
)
from bfabric_app_runner.app_runner.resolve_app import load_workunit_information
from bfabric_app_runner.specs.app.app_version import AppVersion
from bfabric_app_runner.specs.app.commands_spec import CommandsSpec, CommandExec
from bfabric_app_runner.specs.submitter_ref import SubmitterRef


class TestLoadWorkunitInformation:
    @pytest.fixture
    def app_version(self):
        return AppVersion(
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

    @pytest.fixture
    def app_version_yaml(self, app_version) -> str:
        return yaml.safe_dump(app_version.model_dump(mode="json"))

    @pytest.fixture
    def app_version_path(self, fs, app_version_yaml):
        path = Path("/fake/work/app_version.yml")
        fs.create_file(path, contents=app_version_yaml)
        return path

    @pytest.fixture
    def app_spec_module(self, mocker, app_version_yaml) -> str:
        unmocked_read_text = importlib.resources.read_text

        def mocked_read_text(*args, **kwargs):
            if args[0] == "_mocked_package.integrations.bfabric":
                if args[1] == "app.yml":
                    return app_version_yaml
                else:
                    raise NotImplementedError
            else:
                return unmocked_read_text(*args, **kwargs)

        mocker.patch("importlib.resources.read_text").side_effect = mocked_read_text
        return "_mocked_package"

    @pytest.fixture
    def workunit_definition(self):
        return WorkunitDefinition(
            execution=WorkunitExecutionDefinition(
                raw_parameters={"hello": "world"},
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
                storage_output_folder=Path("/fake/remote/path"),
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

    def test_from_module_when_default(self, mocker, app_spec_module, workunit_definition_path, app_version):
        mock_client = mocker.Mock(name="mock_client")
        return_app_version, return_workunit_ref = load_workunit_information(
            app_spec=app_spec_module,
            client=mock_client,
            work_dir=Path("/fake/work"),
            workunit_ref=workunit_definition_path,
        )
        assert return_app_version == app_version
        assert return_workunit_ref == workunit_definition_path

    def test_from_module_when_explicit(self, mocker, app_spec_module, workunit_definition_path, app_version):
        mock_client = mocker.Mock(name="mock_client")
        return_app_version, return_workunit_ref = load_workunit_information(
            app_spec=f"{app_spec_module}.integrations.bfabric:app.yml",
            client=mock_client,
            work_dir=Path("/fake/work"),
            workunit_ref=workunit_definition_path,
        )
        assert return_app_version == app_version
        assert return_workunit_ref == workunit_definition_path

    def test_from_path(self, mocker, app_version_path, workunit_definition_path, app_version):
        mock_client = mocker.Mock(name="mock_client")
        return_app_version, return_workunit_ref = load_workunit_information(
            app_spec=app_version_path,
            client=mock_client,
            work_dir=Path("/fake/work"),
            workunit_ref=workunit_definition_path,
        )
        assert return_app_version == app_version
        assert return_workunit_ref == workunit_definition_path
