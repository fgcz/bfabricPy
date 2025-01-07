import pytest
import yaml

from app_runner.specs.app.app_spec import AppVersion
from app_runner.specs.app.commands_spec import CommandShell, CommandDocker, MountOptions, CommandsSpec


@pytest.fixture()
def parsed() -> AppVersion:
    return AppVersion(
        version="0.0.1",
        commands=CommandsSpec(
            dispatch=CommandShell(command="dispatch"),
            process=CommandDocker(
                image="image", command="command", mounts=MountOptions(read_only=[("/host", "/container")])
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
version: 0.0.1"""


def test_serialize(parsed, serialized):
    assert yaml.safe_dump(parsed.model_dump(mode="json")).strip() == serialized.strip()


def test_parse(parsed, serialized):
    assert AppVersion.model_validate(yaml.safe_load(serialized)) == parsed
