from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

from loguru import logger

from bfabric.bfabric import Bfabric
from bfabric.entities import Resource, Dataset
from bfabric.experimental.app_interface.input_preparation._spec import ResourceSpec, DatasetSpec, SpecType


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

    def clean_all(self, specs: list[SpecType]) -> None:
        for spec in specs:
            logger.debug(f"Cleaning {spec}")
            if isinstance(spec, ResourceSpec):
                self.clean_resource(spec)
            elif isinstance(spec, DatasetSpec):
                self.clean_dataset(spec)
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
        target_path = self._working_dir / spec.filename
        with tempfile.NamedTemporaryFile() as tmp_file:
            dataset.write_csv(Path(tmp_file.name), separator=spec.separator)
            tmp_file.flush()
            tmp_file.seek(0)
            if target_path.exists() and target_path.read_text() == tmp_file.read().decode():
                logger.debug(f"Skipping {spec.filename} as it already exists and has the correct content")
            else:
                tmp_file.seek(0)
                target_path.write_text(tmp_file.read().decode())

    def clean_resource(self, spec: ResourceSpec) -> None:
        name = spec.filename if spec.filename else Resource.find(id=spec.id, client=self._client)["name"]
        path = self._working_dir / name
        if path.exists():
            logger.info(f"Removing {path}")
            path.unlink()
        else:
            logger.debug(f"Resource {path} does not exist")

    def clean_dataset(self, spec: DatasetSpec) -> None:
        path = self._working_dir / spec.filename
        if path.exists():
            logger.info(f"Removing {path}")
            path.unlink()
        else:
            logger.debug(f"Dataset {path} does not exist")


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
