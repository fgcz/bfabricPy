"""Write environment entries to the bfabricpy YAML config file.

Note: ``yaml.dump`` does not preserve YAML comments — any comments in the
existing config file will be lost when the file is rewritten.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bfabric.config.config_file import ConfigFile, EnvironmentConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def _write_config_file(config_path: Path, data: Mapping[str, object]) -> None:
    """Serialize *data* to *config_path* as YAML with ``0o600`` permissions.

    Centralizes the secret-safe write shared by every config mutation: creates parent
    directories, dumps the mapping, and forces ``0o600`` even on a pre-existing file (whose
    permissions ``os.open`` would otherwise leave untouched) so a secret never lands in a
    group/world-readable file.
    """
    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.dump(data, default_flow_style=False, sort_keys=False).encode()
    fd = os.open(str(config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        _ = os.write(fd, serialized)
    finally:
        os.close(fd)


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

    _write_config_file(config_path, existing)


def set_default_config(config_path: Path, env_name: str) -> None:
    """Set ``GENERAL.default_config`` to an already-defined environment.

    Unlike :func:`write_environment_to_config`, this only flips the default -- it never
    creates or modifies an environment. Other environments and the general section are
    preserved.

    :param config_path: Path to the YAML config file (will be expanded).
    :param env_name: Name of an existing environment to mark as default.
    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments; the file is
        left untouched in that case.
    """
    config_path = Path(config_path).expanduser()
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    loaded: object = yaml.safe_load(config_path.read_text())  # pyright: ignore[reportAny]
    existing: dict[str, object]
    existing = loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]

    # Enumerate the configured environments through the reader so the check matches how the
    # file will actually load back. ConfigFile's "before" validators mutate their input in
    # place, so always validate a deep copy and keep ``existing`` pristine for the write.
    # This also doubles as the round-trip guard: since env_name is confirmed to be one of
    # config_file_obj.environments, and environments are otherwise untouched below, setting
    # GENERAL.default_config to env_name cannot fail ConfigFile's own default-config-must-exist
    # validator -- so no second validation pass is needed after the mutation.
    config_file_obj = ConfigFile.model_validate(copy.deepcopy(existing))
    if env_name not in config_file_obj.environments:
        available = ", ".join(sorted(config_file_obj.environments)) or "(none)"
        raise ValueError(f"Environment {env_name!r} is not defined. Available environments: {available}")

    general = existing.setdefault("GENERAL", {})
    if not isinstance(general, dict):
        raise ValueError("Malformed config file: 'GENERAL' section is not a mapping.")
    general["default_config"] = env_name

    _write_config_file(config_path, existing)
