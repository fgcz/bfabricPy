from pathlib import Path, PosixPath

import pytest
import yaml

from bfabric_app_runner.app_env.env_data import EnvData, env_data_from_cli


@pytest.fixture
def sample_env_data():
    """Fixture providing sample environment data."""
    return {
        "APP_RUNNER_APP_SPEC": "/path/to/app_spec.yaml",
        "APP_RUNNER_WORKUNIT_REF": "/path/to/workunit",
        "APP_RUNNER_UV_BIN": "/path/to/uv",
        "APP_RUNNER_UV_PYTHON_VERSION": "3.10",
        "APP_RUNNER_UV_DEPS_STRING": "package1==1.0.0 package2>=2.0.0",
        "BFABRICPY_CONFIG_OVERRIDE": None,
    }


@pytest.fixture
def sample_env_yaml_file(fs, sample_env_data) -> Path:
    """Fixture providing a temporary YAML file with sample environment data."""
    yaml_path = Path("/tmp/test_env_data.yaml")
    fs.create_file(yaml_path, contents=yaml.dump(sample_env_data))
    return yaml_path


def test_env_data_initialization(sample_env_data):
    """Test that EnvData can be initialized with valid data."""
    env_data = EnvData(**sample_env_data)
    assert env_data.app_spec == sample_env_data["APP_RUNNER_APP_SPEC"]
    assert env_data.workunit_ref == Path(sample_env_data["APP_RUNNER_WORKUNIT_REF"])
    assert env_data.uv_bin == Path(sample_env_data["APP_RUNNER_UV_BIN"])
    assert env_data.uv_python_version == sample_env_data["APP_RUNNER_UV_PYTHON_VERSION"]
    assert env_data.deps_string == sample_env_data["APP_RUNNER_UV_DEPS_STRING"]
    assert env_data.config_data == sample_env_data["BFABRICPY_CONFIG_OVERRIDE"]


def test_load_yaml(sample_env_yaml_file, sample_env_data):
    env_data = EnvData.load_yaml(sample_env_yaml_file)
    assert env_data.app_spec == sample_env_data["APP_RUNNER_APP_SPEC"]
    assert env_data.workunit_ref == PosixPath(sample_env_data["APP_RUNNER_WORKUNIT_REF"])
    assert env_data.uv_python_version == sample_env_data["APP_RUNNER_UV_PYTHON_VERSION"]


def test_save_yaml(fs, sample_env_data):
    env_data = EnvData(**sample_env_data)
    save_path = Path("/tmp/saved_env_config.yaml")
    fs.create_file(save_path, contents="")
    env_data.save_yaml(save_path)
    assert save_path.exists()
    with save_path.open("r") as f:
        loaded_data = yaml.safe_load(f)
    assert loaded_data["app_spec"] == env_data.app_spec
    assert loaded_data["workunit_ref"] == str(env_data.workunit_ref)
    assert loaded_data["uv_bin"] == str(env_data.uv_bin)


def test_env_data_from_cli():
    """Test env_data_from_cli with string app_spec."""
    # Test with string app_spec instead of Path
    app_spec_str = "app:spec_identifier"
    workunit_ref = Path("/path/to/workunit")
    uv_bin = Path("/path/to/uv")

    result = env_data_from_cli(
        app_spec=app_spec_str,
        workunit_ref=workunit_ref,
        uv_bin=uv_bin,
        uv_python_version="3.10",
        deps_string="package1==1.0.0",
        config_data=None,
    )

    # Verify app_spec is kept as string
    assert result.app_spec == app_spec_str
    assert isinstance(result.app_spec, str)
    # Other fields should still be resolved
    assert result.workunit_ref == workunit_ref.resolve()
    assert result.uv_bin == uv_bin.resolve()
