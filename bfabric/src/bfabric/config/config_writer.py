"""Write environment entries to the bfabricpy YAML config file.

Note: ``yaml.dump`` does not preserve YAML comments — any comments in the
existing config file will be lost when the file is rewritten.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def write_environment_to_config(
    config_path: Path,
    env_name: str,
    env_data: dict[str, object],
    *,
    set_default: bool = True,
) -> None:
    """Write (or update) an environment section in the bfabricpy YAML config.

    * Creates the file if it does not exist.
    * Merges *env_data* into the target environment, preserving other
      environments.
    * Sets ``GENERAL.default_config`` to *env_name* when *set_default* is
      ``True``.
    * File permissions are set to ``0o600``.

    :param config_path: Path to the YAML config file (will be expanded).
    :param env_name: Name of the environment to create / update.
    :param env_data: Dictionary of fields for the environment.
    :param set_default: If ``True``, set this environment as the default.
    """
    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.is_file():
        loaded: object = yaml.safe_load(config_path.read_text())  # pyright: ignore[reportAny]
        existing: dict[str, dict[str, object]] = loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]
    else:
        existing = {}

    if "GENERAL" not in existing:
        existing["GENERAL"] = {}

    if set_default:
        existing["GENERAL"]["default_config"] = env_name

    existing[env_name] = env_data

    data = yaml.dump(existing, default_flow_style=False, sort_keys=False).encode()
    fd = os.open(str(config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        _ = os.write(fd, data)
    finally:
        os.close(fd)
