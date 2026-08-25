"""Write environment entries to the bfabricpy YAML config file.

Note: rewriting the file drops any YAML comments in it (``yaml.safe_dump`` doesn't preserve them).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import yaml

from bfabric.config.auth_methods import auth_owned_keys
from bfabric.config.config_file import ConfigFile, EnvironmentConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


# Inline secrets cleared by :func:`clear_environment_credentials`. OAuth is absent: its token lives in
# the file cache, so clearing here would report success while leaving the credential in place.
_INLINE_SECRET_KEYS: tuple[str, ...] = ("login", "password", "pat", "client_secret")


def validate_writable_environment(env_data: Mapping[str, object]) -> None:
    """Reject an environment whose auth keys contradict each other, before it reaches disk.

    Reading stays tolerant, because 1.21.0 wrote files without these checks and a user must not be
    locked out of their own config; only newly written environments have to be coherent.

    :raises ValueError: With a message naming the offending combination.
    """
    present = {key for key, value in env_data.items() if value is not None}
    method = env_data.get("auth_method")

    if method == "client_credentials" and "client_secret" not in present:
        raise ValueError("auth_method 'client_credentials' requires a 'client_secret'.")
    if method == "pat" and "pat" not in present:
        raise ValueError("auth_method 'pat' requires a 'pat'.")
    if method == "password" and "login" not in present:
        raise ValueError("auth_method 'password' requires a 'login'.")
    if method in ("oauth", "pat") and "client_secret" in present:
        raise ValueError(f"auth_method {method!r} cannot be combined with a 'client_secret'.")
    if method in ("oauth", "client_credentials", "password") and "pat" in present:
        raise ValueError(f"auth_method {method!r} cannot be combined with a 'pat'.")
    if ("registration_access_token" in present) != ("registration_client_uri" in present):
        raise ValueError(
            "registration_access_token and registration_client_uri must be set together; "
            "either alone cannot manage a client registration."
        )


def read_environment_auth_keys(config_path: Path, env_name: str) -> dict[str, object]:
    """The auth-owned keys currently recorded for *env_name*, empty if it or the file is absent."""
    env = _read_config_file(config_path).get(env_name)
    if not isinstance(env, dict):
        return {}
    owned = auth_owned_keys()
    return {key: value for key, value in cast("dict[str, object]", env).items() if key in owned}


def _plain(value: object) -> object:
    """*value* with ``str`` subclasses (e.g. ``BaseUrl``) unwrapped, which ``safe_dump`` rejects."""
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in cast("dict[object, object]", value).items()}
    return str(value) if isinstance(value, str) else value


def _read_config_file(config_path: Path) -> dict[str, object]:
    """Raw YAML mapping at *config_path*, empty if it is absent or not a mapping."""
    config_path = Path(config_path).expanduser()
    if not config_path.is_file():
        return {}
    loaded: object = yaml.safe_load(config_path.read_text())  # pyright: ignore[reportAny]
    return loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]


def _write_config_file(config_path: Path, data: Mapping[str, object]) -> None:
    """Serialize *data* to *config_path* as YAML, mode ``0o600`` (fchmod forces it on existing files)."""
    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.safe_dump(_plain(data), default_flow_style=False, sort_keys=False).encode()
    fd = os.open(str(config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        _ = os.write(fd, serialized)
    finally:
        os.close(fd)


def _load_for_edit(config_path: Path, env_name: str) -> dict[str, object]:
    """Raw YAML mapping for an in-place edit of *env_name*.

    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments.
    """
    config_path = Path(config_path).expanduser()
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    existing = _read_config_file(config_path)
    environments = ConfigFile.model_validate(existing).environments
    if env_name not in environments:
        available = ", ".join(sorted(environments)) or "(none)"
        raise ValueError(f"Environment {env_name!r} is not defined. Available environments: {available}")
    return existing


def write_environment_to_config(
    config_path: Path,
    env_name: str,
    env_data: Mapping[str, object],
    *,
    auth: Literal["merge", "replace"],
    set_default: bool,
) -> None:
    """Write or update the environment *env_name*, creating the config file (``0o600``) if needed.

    Keys outside the auth group always survive. *auth* decides the rest: ``"replace"`` treats
    *env_data* as the complete auth state, so anything it omits is dropped and a stale secret cannot
    outlive the method that wrote it; ``"merge"`` keeps auth keys *env_data* does not mention, for a
    partial update such as a rotated secret. A key mapped to ``None`` is removed either way.

    It has no default because the two modes corrupt in opposite directions: ``replace`` can strand a
    client by dropping its registration credentials, ``merge`` can resurrect a superseded one.

    :raises pydantic.ValidationError: If the merged environment would not parse back through the
        reader. Checked before any filesystem change.
    :raises ValueError: If *env_name* is reserved, or the merged environment is incoherent.
    """
    if env_name in ("GENERAL", "default"):
        raise ValueError(f"Environment name {env_name!r} is reserved and cannot be used.")
    existing = _read_config_file(config_path)

    owned = auth_owned_keys()
    previous = existing.get(env_name)
    kept: dict[str, object] = {}
    if isinstance(previous, dict):
        kept = {
            key: value
            for key, value in cast("dict[str, object]", previous).items()
            if key not in owned or auth == "merge"
        }
    # Validate the *merged* environment, not just env_data: the merge is what gets persisted.
    merged = {key: value for key, value in (kept | dict(env_data)).items() if value is not None}
    validate_writable_environment(merged)
    _ = EnvironmentConfig.model_validate(dict(merged))

    general = existing.setdefault("GENERAL", {})
    if set_default:
        cast("dict[str, object]", general)["default_config"] = env_name
    existing[env_name] = merged
    _write_config_file(config_path, existing)


def set_default_config(config_path: Path, env_name: str) -> None:
    """Point ``GENERAL.default_config`` at the existing environment *env_name*, changing nothing else.

    :raises FileNotFoundError: If the config file does not exist.
    :raises ValueError: If *env_name* is not among the configured environments; the file is left
        untouched.
    """
    # env_name is known and environments are untouched, so setting the default cannot fail the reader.
    existing = _load_for_edit(config_path, env_name)
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
    existing = _load_for_edit(config_path, env_name)
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
    existing = _load_for_edit(config_path, env_name)
    _ = existing.pop(env_name, None)
    general = existing.get("GENERAL")
    if isinstance(general, dict):
        general_map = cast("dict[str, object]", general)
        if general_map.get("default_config") == env_name:
            _ = general_map.pop("default_config", None)
    _write_config_file(config_path, existing)
