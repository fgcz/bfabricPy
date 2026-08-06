"""Shared parameter resolution for the ``auth`` commands.

Environment, base URL, scope and default-ness may each come from the command line, from the
environment already recorded in the config, or from a prompt. Resolving all of it in one place is what
makes a zero-argument re-login possible: the recorded environment *is* the login recipe.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric_scripts.cli.interactive import confirm, is_interactive, select_choice, select_or_input, text_input
from bfabric_scripts.cli.login._constants import SCOPE_PRESETS, SCOPE_PRESETS_BY_NAME
from bfabric_scripts.cli.login._urls import KNOWN_INSTANCES, normalize_base_url, suggest_env_name

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
    """Resolve the target environment name; ``None`` if cancelled.

    Precedence matches ``Bfabric.connect()`` — explicit, ``BFABRICPY_CONFIG_ENV``, configured default
    — so a login lands where a later connect reads. Prompting happens only when environments exist
    but none is the default, since asking on every login is the prompt a re-login exists to avoid.
    """
    if config_env is not None:
        return config_env
    from_env_var = os.environ.get(CONFIG_ENV_VAR)
    if from_env_var:
        return from_env_var
    loaded = load_config_file(config_file)
    current = loaded.general.default_config if loaded else None
    if current:
        return current
    names = list(loaded.environments) if loaded else []
    if not is_interactive():
        return _FALLBACK_ENV
    return select_or_input("Environment name", names, default=_FALLBACK_ENV)


def resolve_base_url(base_url: str | None, env: EnvironmentConfig | None) -> str | None:
    """Resolve the instance URL: explicit, else the environment's recorded one, else a picker.

    The recorded fallback is what removes the retype from a re-login. ``None`` if cancelled, or if a
    first login has no URL and no terminal to ask on.
    """
    if base_url is not None:
        return normalize_base_url(base_url)
    if env is not None:
        return normalize_base_url(str(env.config.base_url))
    if not is_interactive():
        return None
    return select_instance()


def select_instance() -> str | None:
    """First-login instance picker over :data:`KNOWN_INSTANCES`, plus free-text entry for any other."""
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
    if picked == _CUSTOM:
        typed = text_input("B-Fabric instance URL")
        return normalize_base_url(typed) if typed else None
    return KNOWN_INSTANCES[picked]


def _scope_menu_label(choice: str) -> str:
    """Menu label for a scope preset (description + the scopes it maps to) or the Custom entry."""
    width = max(len(preset.description) for preset in SCOPE_PRESETS)
    if choice == _CUSTOM:
        return f"{'Custom…'.ljust(width)}   (enter scopes manually)"
    preset = SCOPE_PRESETS_BY_NAME[choice]
    return f"{preset.description.ljust(width)}   {preset.scope}"


def resolve_scope(scope: str | None, env: EnvironmentConfig | None = None) -> str | None:
    """Resolve the OAuth scope string, expanding a preset name; ``None`` if cancelled or headless.

    Falls back to the environment's *requested* scope, which is what makes a re-login prompt-free.
    Never the cached token's *granted* scope: that reflects what the server allowed, so replaying it
    would silently bake in a dropped scope forever. There is deliberately no default scope.
    """
    if scope is not None:
        preset = SCOPE_PRESETS_BY_NAME.get(scope)
        return preset.scope if preset is not None else scope
    if env is not None and env.scope:
        return env.scope
    if not is_interactive():
        return None
    picked = select_choice(
        "Select OAuth scope set",
        [preset.name for preset in SCOPE_PRESETS] + [_CUSTOM],
        default=SCOPE_PRESETS[0].name,
        describe=_scope_menu_label,
    )
    if picked is None:
        return None
    if picked == _CUSTOM:
        return text_input("Enter OAuth scopes (space-separated)")
    return SCOPE_PRESETS_BY_NAME[picked].scope


def resolve_set_default(set_default: bool | None, config_env: str, *, is_new_env: bool = False) -> bool | None:
    """Resolve whether the freshly-authenticated environment becomes the config default.

    A re-login into an existing environment doesn't ask, since it changes no defaults; a brand-new one
    prompts, or becomes the default when headless. ``None`` if cancelled.
    """
    if set_default is not None:
        return set_default
    if not is_new_env:
        return False
    if not is_interactive():
        return True
    return confirm(f"Set '{config_env}' as the default environment?", default=True)


def suggest_config_env(base_url: str, existing: list[str]) -> str:
    """A free environment name derived from *base_url*, suffixed if the derived one is taken."""
    name = suggest_env_name(base_url)
    if name not in existing:
        return name
    return next(f"{name}-{suffix}" for suffix in range(2, len(existing) + 3) if f"{name}-{suffix}" not in existing)


def require_mutable_config() -> bool:
    """Whether config-changing commands may run, printing why not when they may not.

    ``BFABRICPY_CONFIG_OVERRIDE`` supplies the whole configuration, so the file a mutating command
    would write is not the config in effect; a silent write to an ignored file is worse than refusing.
    """
    if os.environ.get(CONFIG_OVERRIDE_VAR):
        print(
            f"Refusing to change the config file while {CONFIG_OVERRIDE_VAR} is set: it overrides the "
            f"file, so the change would have no effect. Unset it and try again."
        )
        return False
    return True


def describe_active_reason(env_name: str, default_config: str | None) -> str:
    """Why *env_name* is (or isn't) the environment in effect, as a display suffix.

    Makes the "I ran ``auth activate X`` and nothing changed" case visible: ``BFABRICPY_CONFIG_ENV``
    silently outranks the configured default, and an override outranks the file entirely.
    """
    if os.environ.get(CONFIG_OVERRIDE_VAR):
        return f"  (config pinned by {CONFIG_OVERRIDE_VAR})"
    from_env_var = os.environ.get(CONFIG_ENV_VAR)
    if from_env_var:
        return f"  (active via {CONFIG_ENV_VAR})" if from_env_var == env_name else ""
    return "  (default)" if env_name == default_config else ""
