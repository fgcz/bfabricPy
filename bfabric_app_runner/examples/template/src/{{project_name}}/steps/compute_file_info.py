import hashlib
from pathlib import Path

import yaml


def compute_checksum_sha256(path: Path) -> str:
    """Compute the SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 32), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_file_info(file_path: Path | str) -> dict[str, str | int | None]:
    """Returns a dictionary with information about the file."""
    path = Path(file_path).resolve()
    if not path.exists():
        return {"path": str(path), "size": None, "checksum_sha256": None}
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "checksum_sha256": compute_checksum_sha256(path),
    }


def write_file_info_yaml(file_path: Path | str, yaml_path: Path | str) -> None:
    """Computes the file info for the specified file and dumps the result to a YAML file at `yaml_path`."""
    yaml_path = Path(yaml_path)
    file_info = compute_file_info(file_path)
    yaml_path.write_text(yaml.safe_dump(file_info))
