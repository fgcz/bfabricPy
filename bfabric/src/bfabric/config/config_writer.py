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
    """Serialize *data* to *config_path* as YAML, mode ``0o600`` (fchmod forces it on existing files)."""
    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.dump(data, default_flow_style=False, sort_keys=False).encode()
    fd = os.open(str(config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        _ = os.write(fd, serialized)
    finally:
        os.close(fd)


# Keys an auth command owns outright; replaced wholesale on merge so a stale secret can't be
# resurrected by ``gather_auth`` after re-login via a different method.
_AUTH_OWNED_KEYS = frozenset({"login", "password", "pat", "auth_method", "client_id", "scope"})

# Inline secrets cleared by :func:`clear_environment_credentials`. OAuth is absent: its token lives in
# the file cache, so clearing here would report success while leaving the credential in place.
_INLINE_SECRET_KEYS: tuple[str, ...] = ("login", "password", "pat")


def _validate_round_trip(env_name: str, env_data: Mapping[str, object]) -> None:
    """Raise unless *env_data* is a loadable :class:`EnvironmentConfig` under a non-reserved name."""
    if env_name in ("GENERAL", "default"):
        raise ValueError(f"Environment name {env_name!r} is reserved and cannot be used.")
    _ = EnvironmentConfig.model_validate(dict(env_data))


def _merge_environment(previous: object, env_data: Mapping[str, object]) -> dict[str, object]:
    """Combine an existing environment section with *env_data*, dropping :data:`_AUTH_OWNED_KEYS`
    from *previous* first so hand-written extras survive but stale secrets don't."""
    if not isinstance(previous, dict):
        return dict(env_data)
    kept = {key: value for key, value in cast("dict[str, object]", previous).items() if key not in _AUTH_OWNED_KEYS}
    return kept | dict(env_data)


def write_environment_to_config(
    config_path: Path,
    env_name: str,
    env_data: Mapping[str, object],
    *,
    set_default: bool,
) -> None:
    """Write or update the environment *env_name*, creating the config file (``0o600``) if needed.

    *env_data* is merged into an existing section; see :func:`_merge_environment`.

    :raises pydantic.ValidationError: If the merged environment would not parse back through the
        reader. Checked before any filesystem change.
    """
    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, dict[str, object]]
    if config_path.is_file():
        loaded: object = yaml.safe_load(config_path.read_text())  # pyright: ignore[reportAny]
        existing = loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]
    else:
        existing = {}

    # Validate the *merged* environment, not just env_data: the merge is what gets persisted.
    merged = _merge_environment(existing.get(env_name), env_data)
    _validate_round_trip(env_name, merged)

    if "GENERAL" not in existing:
        existing["GENERAL"] = {}

    if set_default:
        existing["GENERAL"]["default_config"] = env_name

    existing[env_name] = merged

    _write_config_file(config_path, existing)


def _load_for_edit(config_path: Path, env_name: str) -> tuple[Path, dict[str, object]]:
    """Raw YAML mapping for an in-place edit of *env_name*, with its expanded path.

    Membership is checked through the reader, on a deep copy since ``ConfigFile``'s "before"
    validators mutate their input, so the returned mapping stays pristine for the write.

    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments.
    """
    config_path = Path(config_path).expanduser()
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    loaded: object = yaml.safe_load(config_path.read_text())  # pyright: ignore[reportAny]
    existing: dict[str, object]
    existing = loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]

    config_file_obj = ConfigFile.model_validate(copy.deepcopy(existing))
    if env_name not in config_file_obj.environments:
        available = ", ".join(sorted(config_file_obj.environments)) or "(none)"
        raise ValueError(f"Environment {env_name!r} is not defined. Available environments: {available}")
    return config_path, existing


def set_default_config(config_path: Path, env_name: str) -> None:
    """Point ``GENERAL.default_config`` at the existing environment *env_name*, changing nothing else.

    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments; the file is left
        untouched.
    """
    # env_name is known and environments are untouched, so setting the default cannot fail the reader.
    config_path, existing = _load_for_edit(config_path, env_name)

    general = existing.setdefault("GENERAL", {})
    if not isinstance(general, dict):
        raise ValueError("Malformed config file: 'GENERAL' section is not a mapping.")
    general["default_config"] = env_name

    _write_config_file(config_path, existing)


def clear_environment_credentials(config_path: Path, env_name: str) -> tuple[str, ...]:
    """Strip :data:`_INLINE_SECRET_KEYS` from *env_name*, keeping it configured for a later re-login.

    OAuth environments hold no inline secret — theirs is in the token cache.

    :returns: The keys actually removed, so the caller can report what happened.
    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments; the file is left
        untouched.
    """
    config_path, existing = _load_for_edit(config_path, env_name)

    env = existing.get(env_name)
    if not isinstance(env, dict):
        return ()
    env_map = cast("dict[str, object]", env)
    removed = tuple(key for key in _INLINE_SECRET_KEYS if key in env_map)
    for key in removed:
        _ = env_map.pop(key, None)

    if removed:
        _write_config_file(config_path, existing)
    return removed


def remove_environment_from_config(config_path: Path, env_name: str) -> None:
    """Delete the environment *env_name*, clearing ``GENERAL.default_config`` if it pointed there.

    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments; the file is left
        untouched.
    """
    config_path, existing = _load_for_edit(config_path, env_name)

    _ = existing.pop(env_name, None)
    general = existing.get("GENERAL")
    if isinstance(general, dict):
        general_map = cast("dict[str, object]", general)
        if general_map.get("default_config") == env_name:
            _ = general_map.pop("default_config", None)

    _write_config_file(config_path, existing)
