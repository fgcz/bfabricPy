"""Service-account login: record a ``client_credentials`` OAuth client for unattended use."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_writer import merge_auth_owned_keys, write_environment_to_config
from bfabric_scripts.cli.login._common import (
    load_config_file,
    require_mutable_config,
    resolve_config_env,
    resolve_set_default,
)
from bfabric_scripts.cli.login._urls import normalize_base_url

_CLIENT_ID_HELP = "OAuth client ID of the service account (from 'bfabric-cli auth register')."
_CLIENT_SECRET_HELP = "OAuth client secret (prompted if omitted)."
_CONFIG_ENV_HELP = "Environment name (defaults to BFABRICPY_CONFIG_ENV or the default)."
_SET_DEFAULT_HELP = "Set this environment as the default in the config file (prompted if omitted)."
_SCOPE_HELP = "OAuth scope to record for this environment (informational; the server grants the scope)."


def cmd_auth_service_account(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    *,
    client_id: Annotated[str, cyclopts.Parameter(help=_CLIENT_ID_HELP)],
    client_secret: Annotated[str | None, cyclopts.Parameter(help=_CLIENT_SECRET_HELP)] = None,
    scope: Annotated[str | None, cyclopts.Parameter(help=_SCOPE_HELP)] = None,
    config_env: Annotated[str | None, cyclopts.Parameter(help=_CONFIG_ENV_HELP)] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    set_default: Annotated[bool | None, cyclopts.Parameter(help=_SET_DEFAULT_HELP)] = None,
) -> None:
    """Authenticate as a service account via the OAuth client_credentials grant.

    Unlike 'auth login', this needs no browser and no cached token, so it suits cron jobs and
    shell scripts: the secret is stored in the config file and a fresh token is fetched per run.
    """
    if not require_mutable_config():
        return
    config_env = resolve_config_env(config_env, config_file)
    if config_env is None:
        print("Login aborted.", file=sys.stderr)
        return
    loaded = load_config_file(config_file)
    is_new_env = loaded is None or config_env not in loaded.environments
    set_default = resolve_set_default(set_default, config_env, is_new_env=is_new_env)
    if set_default is None:
        print("Login aborted.", file=sys.stderr)
        return

    if client_secret is None:
        client_secret = getpass.getpass("Client secret: ")
    else:
        print("Warning: passing secrets via CLI flags is insecure (visible in ps, shell history).", file=sys.stderr)

    # Stored under ``client_secret``, not ``login``/``password``: an unmodified <=1.19.0 client
    # validates every environment and would reject a non-32-char password, poisoning the shared file.
    env_data: dict[str, object] = {
        "base_url": normalize_base_url(base_url),
        "auth_method": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if scope is not None:
        env_data["scope"] = scope
    # Re-running this is how a secret rotated in the B-Fabric UI gets in, so keep the auth-owned keys
    # it does not set — notably the registration credentials, without which the client can no longer
    # be edited. The writer replaces that whole group at once.
    merged = merge_auth_owned_keys(config_file, config_env, env_data)
    write_environment_to_config(config_file, config_env, merged, set_default=set_default)
    print("Service account configured.")
    print(f"Config saved to environment '{config_env}' in {config_file}")
