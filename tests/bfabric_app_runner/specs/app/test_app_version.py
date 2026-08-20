import pytest
import yaml

from bfabric_app_runner.specs.app.app_version import AppVersion
from bfabric_app_runner.specs.app.commands_spec import (
    CommandShell,
    CommandDocker,
    MountOptions,
    CommandsSpec,
)


@pytest.fixture()
def parsed() -> AppVersion:
    return AppVersion(
        version="0.0.1",
        commands=CommandsSpec(
            dispatch=CommandShell(command="dispatch"),
            process=CommandDocker(
                image="image",
                command="command",
                mounts=MountOptions(read_only=[("/host", "/container")]),
            ),
            collect=CommandShell(command="collect"),
        ),
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
    hostname: null
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
version: 0.0.1"""


def test_serialize(parsed, serialized):
    assert yaml.safe_dump(parsed.model_dump(mode="json")).strip() == serialized.strip()


def test_parse(parsed, serialized):
    assert AppVersion.model_validate(yaml.safe_load(serialized)) == parsed


def test_parse_ignores_removed_reuse_default_resource(parsed, serialized):
    """An app.yml still carrying the removed legacy flag must keep parsing, not be rejected."""
    data = yaml.safe_load(serialized) | {"reuse_default_resource": True}
    app_version = AppVersion.model_validate(data)
    assert app_version == parsed
    assert not hasattr(app_version, "reuse_default_resource")
