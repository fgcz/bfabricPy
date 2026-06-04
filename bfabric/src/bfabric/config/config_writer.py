"""Write environment entries to the bfabricpy YAML config file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def write_environment_to_config(
    config_path: Path,
    env_name: str,
    env_data: dict[str, Any],
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
        existing: dict[str, Any] = yaml.safe_load(config_path.read_text()) or {}
    else:
        existing = {}

    if "GENERAL" not in existing:
        existing["GENERAL"] = {}

    if set_default:
        existing["GENERAL"]["default_config"] = env_name

    existing[env_name] = env_data

    config_path.write_text(yaml.dump(existing, default_flow_style=False, sort_keys=False))
    config_path.chmod(0o600)
