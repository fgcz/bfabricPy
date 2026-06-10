"""Write environment entries to the bfabricpy YAML config file.

Note: ``yaml.dump`` does not preserve YAML comments — any comments in the
existing config file will be lost when the file is rewritten.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bfabric.config.config_file import EnvironmentConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def _validate_round_trip(env_name: str, env_data: Mapping[str, object]) -> None:
    """Reject an environment that the reader could not load back.

    Mirrors the reader's invariants so a write either persists a parseable config or fails
    cleanly without touching the file. Checks two things:

    * The name is not reserved -- the reader treats ``GENERAL`` as the general section and
      forbids ``default``, so neither can be an environment.
    * The fields form a valid :class:`EnvironmentConfig` (e.g. ``base_url`` present, auth
      combination consistent). Only the single environment is validated, not the merged file,
      so a pre-existing legacy environment can't block writing a new, valid one.
    """
    if env_name in ("GENERAL", "default"):
        raise ValueError(f"Environment name {env_name!r} is reserved and cannot be used.")
    _ = EnvironmentConfig.model_validate(dict(env_data))


def write_environment_to_config(
    config_path: Path,
    env_name: str,
    env_data: Mapping[str, object],
    *,
    set_default: bool,
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
    :param set_default: If ``True``, set this environment as the default. Required: callers must
        decide explicitly whether the new environment becomes the default.
    :raises pydantic.ValidationError: If *env_data* would not parse back through the reader
        (e.g. a missing ``base_url`` or an invalid auth combination). Validated before any
        filesystem change, so a rejected write leaves an existing config untouched.
    """
    # Guarantee the round-trip before any filesystem change, so a rejected write leaves an
    # existing config untouched.
    _validate_round_trip(env_name, env_data)

    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, dict[str, object]]
    if config_path.is_file():
        loaded: object = yaml.safe_load(config_path.read_text())  # pyright: ignore[reportAny]
        existing = loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]
    else:
        existing = {}

    if "GENERAL" not in existing:
        existing["GENERAL"] = {}

    if set_default:
        existing["GENERAL"]["default_config"] = env_name

    existing[env_name] = dict(env_data)

    data = yaml.dump(existing, default_flow_style=False, sort_keys=False).encode()
    fd = os.open(str(config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        # The mode passed to os.open is only honored when the file is created; an existing
        # config keeps its old (possibly group/world-readable) permissions. Tighten explicitly
        # so a secret written here (e.g. a PAT) never lands in a readable file.
        os.fchmod(fd, 0o600)
        _ = os.write(fd, data)
    finally:
        os.close(fd)
