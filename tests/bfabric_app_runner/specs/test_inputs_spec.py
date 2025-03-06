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


def test_serialize(parsed, serialized):
    assert yaml.safe_dump(parsed.model_dump(mode="json")).strip() == serialized.strip()


def test_parse(parsed, serialized):
    assert InputsSpec.model_validate(yaml.safe_load(serialized)) == parsed
