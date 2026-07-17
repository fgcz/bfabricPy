"""Write environment entries to the bfabricpy YAML config file.

Note: rewriting the file drops any YAML comments in it (``yaml.dump`` doesn't preserve them).
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml

from bfabric.config.config_file import ConfigFile, EnvironmentConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


def _write_config_file(config_path: Path, data: Mapping[str, object]) -> None:
    """Serialize *data* to *config_path* as YAML, always ``0o600`` so a secret never lands in a
    group/world-readable file.

    The explicit ``fchmod`` forces the mode even on a pre-existing file, whose permissions
    ``os.open`` would otherwise leave untouched.
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
    """Reject an environment the reader could not load back, so a write either persists a parseable
    config or fails without touching the file.

    Rejects the reserved names (``GENERAL`` is the general section, ``default`` is forbidden) and
    anything that isn't a valid :class:`EnvironmentConfig`. Only this one environment is validated,
    not the merged file, so a pre-existing legacy environment can't block writing a new valid one.
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
    """Write (or update) an environment section in the bfabricpy YAML config, creating the file
    (mode ``0o600``) if needed and preserving other environments. Sets ``GENERAL.default_config``
    to *env_name* when *set_default*.

    :param config_path: Path to the YAML config file (will be expanded).
    :param env_name: Name of the environment to create / update.
    :param env_data: Fields for the environment.
    :param set_default: Whether this environment becomes the default. Required: callers must decide
        explicitly.
    :raises pydantic.ValidationError: If *env_data* would not parse back through the reader (e.g. a
        missing ``base_url`` or an invalid auth combination). Checked before any filesystem change,
        so a rejected write leaves an existing config untouched.
    """
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

    Only flips the default; never creates or modifies an environment.

    :param config_path: Path to the YAML config file (will be expanded).
    :param env_name: Name of an existing environment to mark as default.
    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments; the file is left
        untouched.
    """
    config_path = Path(config_path).expanduser()
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    loaded: object = yaml.safe_load(config_path.read_text())  # pyright: ignore[reportAny]
    existing: dict[str, object]
    existing = loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]

    # Validate through the reader (on a deep copy — ConfigFile's "before" validators mutate their
    # input in place) so the membership check matches how the file loads back, keeping ``existing``
    # pristine for the write. This doubles as the round-trip guard: env_name is a known environment
    # and the environments are untouched below, so setting the default can't fail the reader after.
    config_file_obj = ConfigFile.model_validate(copy.deepcopy(existing))
    if env_name not in config_file_obj.environments:
        available = ", ".join(sorted(config_file_obj.environments)) or "(none)"
        raise ValueError(f"Environment {env_name!r} is not defined. Available environments: {available}")

    general = existing.setdefault("GENERAL", {})
    if not isinstance(general, dict):
        raise ValueError("Malformed config file: 'GENERAL' section is not a mapping.")
    general["default_config"] = env_name

    _write_config_file(config_path, existing)


def remove_environment_from_config(config_path: Path, env_name: str) -> None:
    """Delete an environment section from the bfabricpy YAML config.

    Also clears ``GENERAL.default_config`` if it pointed at *env_name* — otherwise the reader would
    refuse to load a file whose default names a missing environment.

    :param config_path: Path to the YAML config file (will be expanded).
    :param env_name: Name of an existing environment to remove.
    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments; the file is left
        untouched.
    """
    config_path = Path(config_path).expanduser()
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    loaded: object = yaml.safe_load(config_path.read_text())  # pyright: ignore[reportAny]
    existing: dict[str, object]
    existing = loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]

    # Enumerate through the reader so the membership check matches how the file loads back.
    # ConfigFile's "before" validators mutate their input in place, so validate a deep copy and
    # keep ``existing`` pristine for the write.
    config_file_obj = ConfigFile.model_validate(copy.deepcopy(existing))
    if env_name not in config_file_obj.environments:
        available = ", ".join(sorted(config_file_obj.environments)) or "(none)"
        raise ValueError(f"Environment {env_name!r} is not defined. Available environments: {available}")

    _ = existing.pop(env_name, None)
    general = existing.get("GENERAL")
    if isinstance(general, dict):
        general_map = cast("dict[str, object]", general)
        if general_map.get("default_config") == env_name:
            _ = general_map.pop("default_config", None)

    _write_config_file(config_path, existing)
