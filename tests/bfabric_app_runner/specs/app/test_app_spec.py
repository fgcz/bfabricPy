from pathlib import Path

import pytest

from bfabric_app_runner.specs.app.app_spec import AppSpec


@pytest.fixture()
def parsed():
    app_yaml = Path(__file__).parent / "test_versions.yml"
    return AppSpec.load_yaml(app_yaml=app_yaml, app_id="1000", app_name="yyy")


def test_available_versions(parsed):
    assert parsed.available_versions == {"0.1.0", "0.1.1", "1.0.0", "1.0.1"}


def test_hardcoded_single_variant(parsed):
    assert parsed["0.1.0"].commands.dispatch.command == 'echo "0.1.0"'


def test_parametric_single_variant(parsed):
    assert parsed["0.1.1"].commands.dispatch.command == 'echo "0.1.1"'


def test_parametric_multiple_variants(parsed):
    assert parsed["1.0.0"].commands.dispatch.command == 'echo "1.0.0"'
    assert parsed["1.0.1"].commands.dispatch.command == 'echo "1.0.1"'


def test_substitute_app_id(parsed):
    assert parsed["0.1.0"].commands.process.command == 'echo "1000"'


def test_reject_duplicates(parsed):
    version = parsed["0.1.0"]
    with pytest.raises(ValueError) as e:
        AppSpec(bfabric=parsed.bfabric, versions=[version, version])
    assert "Duplicate versions found" in str(e.value)
