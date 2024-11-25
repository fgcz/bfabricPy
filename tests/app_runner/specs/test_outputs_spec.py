import pytest
import yaml

from app_runner.specs.outputs_spec import OutputsSpec, CopyResourceSpec, SaveDatasetSpec


@pytest.fixture()
def parsed() -> OutputsSpec:
    return OutputsSpec(
        outputs=[
            CopyResourceSpec(
                local_path="local_path",
                store_entry_path="store_entry_path",
                store_folder_path=None,
                update_existing="no",
                protocol="scp",
            ),
            SaveDatasetSpec(
                local_path="local_path", separator="separator", name=None, has_header=True, invalid_characters=""
            ),
        ]
    )


@pytest.fixture()
def serialized() -> str:
    return """outputs:
- local_path: local_path
  protocol: scp
  store_entry_path: store_entry_path
  store_folder_path: null
  type: bfabric_copy_resource
  update_existing: 'no'
- has_header: true
  invalid_characters: ''
  local_path: local_path
  name: null
  separator: separator
  type: bfabric_dataset"""


def test_serialize(parsed, serialized):
    assert yaml.safe_dump(parsed.model_dump(mode="json")).strip() == serialized.strip()


def test_parse(parsed, serialized):
    assert OutputsSpec.model_validate(yaml.safe_load(serialized)) == parsed
