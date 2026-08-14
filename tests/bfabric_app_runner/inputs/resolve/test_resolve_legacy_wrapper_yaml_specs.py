import pytest
import yaml
from bfabric_app_runner.inputs.resolve._resolve_legacy_wrapper_yaml_specs import ResolveLegacyWrapperYamlSpecs
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile
from bfabric_app_runner.specs.inputs.legacy_wrapper_yaml_spec import LegacyWrapperYamlSpec


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture
def mock_build(mocker):
    return mocker.patch(
        "bfabric_app_runner.inputs.resolve._resolve_legacy_wrapper_yaml_specs.build_legacy_wrapper_yaml",
        return_value={"application": {"protocol": "scp"}},
    )


@pytest.fixture
def resolver(mock_client):
    return ResolveLegacyWrapperYamlSpecs(client=mock_client)


@pytest.fixture
def spec():
    return LegacyWrapperYamlSpec(filename="config.yaml", workunit_id=1234, output_path="/work/chunk/result.zip")


def test_call(resolver, spec, mock_build):
    result = resolver([spec])
    assert result == [ResolvedStaticFile(filename="config.yaml", content=yaml.safe_dump(mock_build.return_value))]


def test_call_passes_spec_fields_through(resolver, mock_client, mock_build):
    spec = LegacyWrapperYamlSpec(
        filename="config.yaml", workunit_id=1234, output_path="/work/chunk/result.zip", executable="/opt/legacy.bash"
    )
    resolver([spec])
    mock_build.assert_called_once_with(
        client=mock_client,
        workunit_id=1234,
        output_path="/work/chunk/result.zip",
        executable="/opt/legacy.bash",
    )


def test_call_when_empty(resolver):
    assert resolver([]) == []
