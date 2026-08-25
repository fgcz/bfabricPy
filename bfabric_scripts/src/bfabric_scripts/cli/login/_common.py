"""Shared parameter resolution for the ``auth`` commands.

Each value comes from the command line, the recorded environment, or a prompt — which is what makes a
zero-argument re-login possible: the recorded environment *is* the login recipe.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric.config.config_writer import read_environment_auth_keys, write_environment_to_config
from bfabric_scripts.cli.interactive import confirm, is_interactive, select_choice, select_or_input, text_input
from bfabric_scripts.cli.login._constants import SCOPE_PRESETS, SCOPE_PRESETS_BY_NAME
from bfabric.config import BaseUrl
from bfabric_scripts.cli.login._urls import KNOWN_INSTANCES, normalize_base_url

if TYPE_CHECKING:
    from collections.abc import Mapping

# Interactive-only sentinel: choosing it opens a free-text prompt.
_CUSTOM = "custom"

# Fallback environment name when none is configured and none is given (historical default).
_FALLBACK_ENV = "PRODUCTION"

CONFIG_ENV_VAR = "BFABRICPY_CONFIG_ENV"
CONFIG_OVERRIDE_VAR = "BFABRICPY_CONFIG_OVERRIDE"


def load_config_file(config_file: Path) -> ConfigFile | None:
    """Parse the config file, or ``None`` if it does not exist yet."""
    config_path = Path(config_file).expanduser()
    if not config_path.is_file():
        return None
    return ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))


def resolve_config_env(config_env: str | None, config_file: Path) -> str | None:
    """Resolve the target environment name (``Bfabric.connect()`` precedence); ``None`` if cancelled."""
    resolved = config_env or os.environ.get(CONFIG_ENV_VAR)
    if resolved:
        return resolved
    # Loaded only now: an explicit name or env var must not make a malformed config file fatal.
    loaded = load_config_file(config_file)
    if loaded and loaded.general.default_config:
        return loaded.general.default_config
    if not is_interactive():
        return _FALLBACK_ENV
    return select_or_input("Environment name", list(loaded.environments) if loaded else [], default=_FALLBACK_ENV)


def active_config_env(config_env: str | None, config: ConfigFile) -> str | None:
    """The environment a non-login command acts on, without prompting or defaulting; ``None`` if undetermined."""
    return config_env or os.environ.get(CONFIG_ENV_VAR) or config.general.default_config


def _pick_or_type(message: str, labels: dict[str, str], prompt: str) -> str | None:
    """Pick one of *labels* (first preselected), or type a value via the ``_CUSTOM`` entry; ``None`` if cancelled."""
    picked = select_choice(message, [*labels], default=next(iter(labels)), describe=lambda choice: labels[choice])
    if picked is None:
        return None
    return text_input(prompt) if picked == _CUSTOM else picked


def resolve_base_url(base_url: str | None, env: EnvironmentConfig | None) -> BaseUrl | None:
    """Resolve the instance URL: explicit, else the environment's recorded one, else a picker."""
    if base_url is not None:
        return normalize_base_url(base_url)
    if env is not None:
        return env.config.base_url
    if not is_interactive():
        return None
    # First-login picker over the known instances, plus free-text entry.
    labels = {name: f"{name.ljust(10)} {url}" for name, url in KNOWN_INSTANCES.items()}
    labels[_CUSTOM] = f"{'other…'.ljust(10)} (enter a URL)"
    picked = _pick_or_type("Select the B-Fabric instance", labels, "B-Fabric instance URL")
    if not picked:
        return None
    return KNOWN_INSTANCES.get(picked) or normalize_base_url(picked)


def resolve_scope(scope: str | None, env: EnvironmentConfig | None = None) -> str | None:
    """Resolve the OAuth scope string, expanding a preset name; ``None`` if cancelled or headless.

    Falls back to the environment's *requested* scope, never the granted one (see :class:`EnvironmentConfig`).
    """
    if scope is not None:
        preset = SCOPE_PRESETS_BY_NAME.get(scope)
        return preset.scope if preset is not None else scope
    if env is not None and env.scope:
        return env.scope
    if not is_interactive():
        return None
    width = max(len(preset.description) for preset in SCOPE_PRESETS)
    labels = {preset.name: f"{preset.description.ljust(width)}   {preset.scope}" for preset in SCOPE_PRESETS}
    labels[_CUSTOM] = f"{'Custom…'.ljust(width)}   (enter scopes manually)"
    picked = _pick_or_type("Select OAuth scope set", labels, "Enter OAuth scopes (space-separated)")
    if picked is None:
        return None
    preset = SCOPE_PRESETS_BY_NAME.get(picked)
    return preset.scope if preset is not None else picked


def resolve_set_default(set_default: bool | None, config_env: str, *, is_new_env: bool = False) -> bool | None:
    """Whether the environment becomes the config default — a re-login never asks; ``None`` if cancelled."""
    if set_default is not None:
        return set_default
    if not is_new_env:
        return False
    if not is_interactive():
        return True
    return confirm(f"Set '{config_env}' as the default environment?", default=True)


def require_mutable_config() -> bool:
    """Whether config-changing commands may run, printing why not when they may not."""
    if os.environ.get(CONFIG_OVERRIDE_VAR):
        print(
            f"Refusing to change the config file while {CONFIG_OVERRIDE_VAR} is set: it overrides the "
            f"file, so the change would have no effect. Unset it and try again."
        )
        return False
    return True


def describe_active_reason(env_name: str, default_config: str | None) -> str:
    """Why *env_name* is (or isn't) the environment in effect, as a display suffix."""
    if os.environ.get(CONFIG_OVERRIDE_VAR):
        return f"  (config pinned by {CONFIG_OVERRIDE_VAR})"
    from_env_var = os.environ.get(CONFIG_ENV_VAR)
    if from_env_var:
        return f"  (active via {CONFIG_ENV_VAR})" if from_env_var == env_name else ""
    return "  (default)" if env_name == default_config else ""


SAVE_ENV_HELP = "Save the new client to this config environment (keeps its registration credentials)."
FORCE_HELP = "Overwrite the --save-env environment even if it is already configured."


def save_registration(
    result: Mapping[str, object],
    *,
    base_url: str,
    config_file: Path,
    env_name: str,
    is_service_account: bool,
    force: bool = False,
) -> None:
    """Persist a registration response to *env_name* so the client is usable and editable.

    Refuses an environment that already exists unless *force*. Untouched auth-owned keys are carried
    over, so nothing is stripped — but ``client_id`` is replaced, and an interactive OAuth
    environment keys its token cache on it. Saving a new client into one leaves ``auth_method:
    oauth`` pointing at a client with no cached token, so the next connect fails.

    :param is_service_account: Whether this client is meant to authenticate as a service account.
        Only then is ``auth_method: client_credentials`` recorded — it reroutes every later
        ``connect()`` through the stored secret, which is wrong for a client whose users log in
        interactively even when it *has* the grant.
    :raises SystemExit: *env_name* already exists and *force* is false.
    """
    loaded = load_config_file(config_file)
    if not force and loaded is not None and env_name in loaded.environments:
        print(
            f"Error: environment '{env_name}' already exists in {config_file}. Saving into it would "
            f"replace its stored credentials. Pass a new --save-env name, or --force to overwrite.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    env_data: dict[str, object] = {"base_url": normalize_base_url(base_url)}
    for key in ("client_id", "client_secret", "registration_access_token", "registration_client_uri"):
        value = result.get(key)
        if value is not None:
            env_data[key] = value
    if is_service_account and result.get("client_secret"):
        env_data["auth_method"] = "client_credentials"
    write_environment_to_config(config_file, env_name, env_data, auth="merge", set_default=False)
    merged = read_environment_auth_keys(config_file, env_name)
    print(f"Saved to environment '{env_name}' in {config_file}", file=sys.stderr)
    if not (merged.get("registration_access_token") and merged.get("registration_client_uri")):
        # Say it now: otherwise this surfaces only when someone tries to fix a wrong redirect URI,
        # by which time the one-time token is unrecoverable.
        print(
            f"Warning: the server returned no registration credentials, so this client cannot be "
            f"edited later with 'bfabric-cli auth client-update' or removed with 'auth "
            f"client-delete'. Re-register it to change its settings.",
            file=sys.stderr,
        )
