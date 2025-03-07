from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
import yaml
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from bfabric_app_runner.specs.inputs_spec import InputsSpec


@pytest.fixture()
def parsed() -> InputsSpec:
    return InputsSpec(
        inputs=[
            BfabricResourceSpec(
                id=1,
                filename="filename",
                check_checksum=True,
            ),
            BfabricDatasetSpec(
                id=2,
                filename="filename",
                separator=",",
            ),
        ]
    )


@pytest.fixture()
def serialized() -> str:
    return """inputs:
- check_checksum: true
  filename: filename
  id: 1
  type: bfabric_resource
- filename: filename
  id: 2
  separator: ','
  type: bfabric_dataset"""


def test_write_yaml(parsed):
    with NamedTemporaryFile() as file:
        InputsSpec.write_yaml(parsed.inputs, Path(file.name))
        file.seek(0)
        serialized = file.read()
    assert yaml.safe_load(serialized) == parsed.model_dump(mode="json")


def test_read_yaml(parsed, serialized):
    with NamedTemporaryFile() as file:
        file.write(serialized.encode())
        file.seek(0)
        assert InputsSpec.read_yaml(Path(file.name)) == parsed
