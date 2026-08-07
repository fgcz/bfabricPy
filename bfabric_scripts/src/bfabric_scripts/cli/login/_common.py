"""Shared parameter resolution for the ``auth`` commands.

Each value comes from the command line, the recorded environment, or a prompt — which is what makes a
zero-argument re-login possible: the recorded environment *is* the login recipe.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric_scripts.cli.interactive import confirm, is_interactive, select_choice, select_or_input, text_input
from bfabric_scripts.cli.login._constants import SCOPE_PRESETS, SCOPE_PRESETS_BY_NAME
from bfabric_scripts.cli.login._urls import KNOWN_INSTANCES, normalize_base_url

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


def resolve_base_url(base_url: str | None, env: EnvironmentConfig | None) -> str | None:
    """Resolve the instance URL: explicit, else the environment's recorded one, else a picker."""
    if base_url is not None:
        return normalize_base_url(base_url)
    if env is not None:
        return normalize_base_url(str(env.config.base_url))
    if not is_interactive():
        return None
    # First-login picker over the known instances, plus free-text entry.
    labels = {name: f"{name.ljust(10)} {url}" for name, url in KNOWN_INSTANCES.items()}
    labels[_CUSTOM] = f"{'other…'.ljust(10)} (enter a URL)"
    picked = select_choice(
        "Select the B-Fabric instance",
        [*KNOWN_INSTANCES, _CUSTOM],
        default=next(iter(KNOWN_INSTANCES)),
        describe=lambda choice: labels[choice],
    )
    if picked is None:
        return None
    if picked != _CUSTOM:
        return KNOWN_INSTANCES[picked]
    typed = text_input("B-Fabric instance URL")
    return normalize_base_url(typed) if typed else None


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
    picked = select_choice(
        "Select OAuth scope set",
        [*labels],
        default=SCOPE_PRESETS[0].name,
        describe=lambda choice: labels[choice],
    )
    if picked is None:
        return None
    if picked == _CUSTOM:
        return text_input("Enter OAuth scopes (space-separated)")
    return SCOPE_PRESETS_BY_NAME[picked].scope


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
