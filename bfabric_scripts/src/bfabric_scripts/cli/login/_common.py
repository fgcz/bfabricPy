"""Shared parameter resolution for the ``auth`` commands.

Everything a login needs — environment, base URL, scope, whether it becomes the default — may come
from the command line, from the environment already recorded in the config, or from an interactive
prompt. Resolving all of it in one place is what makes a zero-argument re-login possible: the
recorded environment *is* the login recipe.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import yaml

from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric_scripts.cli.interactive import confirm, is_interactive, select_choice, select_or_input, text_input
from bfabric_scripts.cli.login._constants import SCOPE_PRESETS, SCOPE_PRESETS_BY_NAME
from bfabric_scripts.cli.login._instances import KNOWN_INSTANCES, match_instance, suggest_env_name

# Interactive-only sentinel: choosing it opens a free-text prompt for raw scopes.
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
    """Resolve the target environment name.

    The precedence matches :meth:`ConfigFile.get_selected_config_env` and ``Bfabric.connect()`` —
    explicit, then ``BFABRICPY_CONFIG_ENV``, then the configured default — so a login lands in the
    same environment a subsequent connect would read, and a re-login needs no argument.

    Only a genuinely ambiguous case prompts: environments exist but none is the default, so there is
    nothing to resolve to. Otherwise the resolution is used as-is, because asking about it on every
    login is the prompt a zero-argument re-login exists to avoid. ``None`` if cancelled.
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


def normalize_base_url(raw: str) -> str:
    """Normalise a typed base URL deterministically and offline.

    Defaults the scheme to https, lowercases the host, drops a trailing slash, and expands a bare
    known host to that instance's full base URL.

    :raises ValueError: If *raw* is empty or not http(s) — rejected here rather than several minutes
        later, after the browser flow, where the only signal today is an ``httpx.InvalidURL``.
    """
    candidate = raw.strip()
    if not candidate:
        raise ValueError("Base URL must not be empty.")
    if "//" not in candidate:
        candidate = f"https://{candidate}"
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"Base URL must use http or https, got {parts.scheme!r}.")
    if not parts.netloc:
        raise ValueError(f"Base URL {raw!r} has no host.")
    normalized = urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
    instance = match_instance(normalized)
    # Only expand a bare host: an explicit path is the user's, and rewriting it would turn a correct
    # URL for an unusual deployment into a broken one.
    if instance is not None and not parts.path.strip("/"):
        return instance.base_url
    return normalized


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
    """First-login instance picker over :data:`KNOWN_INSTANCES`, plus a free-text entry for any other."""
    labels = {instance.name: f"{instance.name.ljust(10)} {instance.base_url}" for instance in KNOWN_INSTANCES}
    labels[_CUSTOM] = f"{'other…'.ljust(10)} (enter a URL)"
    picked = select_choice(
        "Select the B-Fabric instance",
        [instance.name for instance in KNOWN_INSTANCES] + [_CUSTOM],
        default=KNOWN_INSTANCES[0].name,
        describe=lambda choice: labels[choice],
    )
    if picked is None:
        return None
    if picked == _CUSTOM:
        typed = text_input("B-Fabric instance URL")
        return normalize_base_url(typed) if typed else None
    return next(instance.base_url for instance in KNOWN_INSTANCES if instance.name == picked)


def _scope_menu_label(choice: str) -> str:
    """Menu label for a scope preset (description + the scopes it maps to) or the Custom entry."""
    width = max(len(preset.description) for preset in SCOPE_PRESETS)
    if choice == _CUSTOM:
        return f"{'Custom…'.ljust(width)}   (enter scopes manually)"
    preset = SCOPE_PRESETS_BY_NAME[choice]
    return f"{preset.description.ljust(width)}   {preset.scope}"


def resolve_scope(scope: str | None, env: EnvironmentConfig | None = None) -> str | None:
    """Resolve the OAuth scope string.

    A given *scope* expands preset names and passes anything else through unchanged; otherwise the
    environment's recorded scope is replayed, which is what makes a re-login prompt-free. Failing
    both, an interactive run picks a preset (least-privilege preselected) or types raw scopes, and a
    headless one returns ``None`` so the caller can abort — there is deliberately no default scope.

    The cached token's *granted* scope is never used here: it reflects what the server allowed, so
    replaying it would silently bake in a dropped scope forever.
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

    Explicit *set_default* wins. A re-login into an existing environment doesn't ask — it changes no
    defaults, so the answer is "leave it as it is"; a brand-new environment prompts (yes preselected)
    or, headless, becomes the default. ``None`` if cancelled (the caller aborts).
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

    ``BFABRICPY_CONFIG_OVERRIDE`` supplies the whole configuration from the environment, so the file
    a mutating command would write is not the config in effect — a silent write to an ignored file is
    worse than a refusal.
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
