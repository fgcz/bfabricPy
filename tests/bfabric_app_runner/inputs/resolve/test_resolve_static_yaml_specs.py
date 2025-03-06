import pytest
from bfabric_app_runner.inputs.resolve._resolve_static_yaml_specs import ResolveStaticYamlSpecs
from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec


@pytest.fixture
def resolver():
    return ResolveStaticYamlSpecs()


def test_resolve_static_yaml_specs(resolver):
    spec = StaticYamlSpec(data={"key": "value"}, filename="test.yaml")
    result = resolver([spec, spec])
    assert len(result) == 2
    assert result[0].filename == "test.yaml"
    assert result[0].content == "key: value\n"
    assert result[1].filename == "test.yaml"
    assert result[1].content == "key: value\n"
