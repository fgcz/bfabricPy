from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from bfabric.cli_formatting import setup_script_logging
from bfabric.entities import Resource, Dataset
from bfabric.experimental.app_interface.input_preparation._inputs_spec import ResourceSpec, DatasetSpec, InputsSpec

if TYPE_CHECKING:
    from bfabric.bfabric import Bfabric

    SpecType = ResourceSpec | DatasetSpec


class PrepareInputs:
    def __init__(self, client: Bfabric, working_dir: Path, ssh_user: str | None) -> None:
        self._client = client
        self._working_dir = working_dir
        self._ssh_user = ssh_user

    def prepare_all(self, specs: list[SpecType]) -> None:
        for spec in specs:
            logger.debug(f"Preparing {spec}")
            if isinstance(spec, ResourceSpec):
                self.prepare_resource(spec)
            elif isinstance(spec, DatasetSpec):
                self.prepare_dataset(spec)
            else:
                raise ValueError(f"Unknown spec type: {type(spec)}")

    def prepare_resource(self, spec: ResourceSpec) -> None:
        resource = Resource.find(id=spec.id, client=self._client)

        # determine path to copy from
        scp_uri = f"{resource.storage.scp_prefix}{resource['relativepath']}"

        # determine path to copy to
        result_name = spec.filename if spec.filename else resource["name"]
        result_path = self._working_dir / result_name

        # copy if necessary
        if result_path.exists() and _md5sum(result_path) == resource["filechecksum"]:
            logger.debug(f"Skipping {resource['name']} as it already exists and has the correct checksum")
        else:
            _scp(scp_uri, str(result_path), user=self._ssh_user)

            # verify checksum
            if spec.check_checksum:
                actual_checksum = _md5sum(result_path)
                logger.debug(f"Checksum: expected {resource['filechecksum']}, got {actual_checksum}")
                if actual_checksum != resource["filechecksum"]:
                    raise ValueError(f"Checksum mismatch: expected {resource['filechecksum']}, got {actual_checksum}")

    def prepare_dataset(self, spec: DatasetSpec) -> None:
        dataset = Dataset.find(id=spec.id, client=self._client)
        dataset.write_csv(self._working_dir / spec.filename, separator=spec.separator)


def _is_remote(path: str | Path) -> bool:
    return ":" in str(path)


def _scp(source: str | Path, target: str | Path, *, user: str | None = None) -> None:
    """Performs scp source target.
    Make sure that either the source or target specifies a host, otherwise you should just use shutil.copyfile.
    """
    source_remote = _is_remote(source)
    target_remote = _is_remote(target)
    if source_remote == target_remote:
        msg = (
            f"Either source or target should be remote, but not both. "
            f"source_remote={repr(source_remote)} == target_remote={repr(target_remote)}"
        )
        raise ValueError(msg)
    if user and source_remote:
        source = f"{user}@{source}"
    elif user and target_remote:
        target = f"{user}@{target}"
    if not target_remote:
        Path(target).parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"scp {source} {target}")
    subprocess.run(["scp", source, target], check=True)


def _md5sum(file: Path) -> str:
    hasher = hashlib.md5()
    with file.open("rb") as f:
        for chunk in iter(lambda: f.read(16384), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def prepare_folder(inputs_yaml: Path, target_folder: Path | None, client: Bfabric, ssh_user: str | None) -> None:
    # set defaults
    inputs_yaml = inputs_yaml.absolute()
    if target_folder is None:
        target_folder = inputs_yaml.parent

    # parse the specs
    specs_list = InputsSpec.read_yaml(inputs_yaml)

    # prepare the folder
    prepare = PrepareInputs(client=client, working_dir=target_folder, ssh_user=ssh_user)
    prepare.prepare_all(specs=specs_list)


def main():
    setup_script_logging()
    client = Bfabric.from_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs-yaml", type=Path, required=True)
    parser.add_argument("--target-folder", type=Path, required=False)
    parser.add_argument("--ssh-user", type=str, required=False)
    args = parser.parse_args()
    prepare_folder(
        inputs_yaml=args.inputs_yaml, target_folder=args.target_folder, ssh_user=args.ssh_user, client=client
    )


if __name__ == "__main__":
    main()
