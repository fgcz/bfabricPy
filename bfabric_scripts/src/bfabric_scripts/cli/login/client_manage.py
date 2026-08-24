"""Inspect and edit an OAuth client's own registration (RFC 7592).

Uses the ``registration_access_token`` recorded at registration time, so a misconfigured client
(e.g. a wrong redirect URI) can be corrected without re-registering it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_writer import read_environment_auth_keys, write_environment_to_config
from bfabric.oauth import delete_client, read_client, update_client
from bfabric_scripts.cli.interactive import confirm, is_interactive
from bfabric_scripts.cli.login._common import load_config_file, resolve_config_env

_CONFIG_ENV_HELP = "Environment holding the client's registration credentials."
_REDIRECT_URI_HELP = "Replace the client's redirect URI."
_CLIENT_NAME_HELP = "Replace the client's human-readable name."
_SCOPE_HELP = "Replace the client's scope."
_NO_CONFIRM_HELP = "Delete without asking for confirmation."


def _persist_rotated_credentials(result: dict[str, object], env_name: str, config_file: Path) -> None:
    """Re-save any credential the server rotated on update, so the client stays manageable.

    B-Fabric reissues ``registration_access_token`` (and sometimes ``client_secret``) on a successful
    update and revokes the old one, so a run that only printed them would leave the stored copy dead.

    A credential echoed back unchanged is not a rotation, so it is compared against the stored value
    rather than merely tested for presence — otherwise a server that returns the current secret would
    report a rotation that never happened.
    """
    stored = read_environment_auth_keys(config_file, env_name)
    rotated = {
        key: result[key]
        for key in ("registration_access_token", "client_secret")
        if isinstance(result.get(key), str) and result[key] != stored.get(key)
    }
    if not rotated:
        return
    write_environment_to_config(config_file, env_name, rotated, auth="merge", set_default=False)
    print(f"Updated {', '.join(sorted(rotated))} for environment '{env_name}'.", file=sys.stderr)


def _resolve_registration(config_env: str | None, config_file: Path) -> tuple[str, str, str]:
    """The ``(env_name, registration_client_uri, registration_access_token)`` for the environment.

    :raises SystemExit: The environment is unknown or holds no registration credentials.
    """
    resolved_env = resolve_config_env(config_env, config_file)
    loaded = load_config_file(config_file)
    if resolved_env is None or loaded is None or resolved_env not in loaded.environments:
        print(f"Error: environment '{resolved_env}' not found in {config_file}.", file=sys.stderr)
        raise SystemExit(1)
    env = loaded.environments[resolved_env]
    if env.registration_access_token is None or env.registration_client_uri is None:
        print(
            f"Error: environment '{resolved_env}' has no registration_access_token / "
            f"registration_client_uri recorded. Only a client registered with "
            f"'bfabric-cli auth register --save-env' can be edited this way.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return resolved_env, env.registration_client_uri, env.registration_access_token.get_secret_value()


def cmd_auth_client_show(
    *,
    config_env: Annotated[str | None, cyclopts.Parameter(help=_CONFIG_ENV_HELP)] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
) -> None:
    """Show an OAuth client's current registration as recorded on the server."""
    _, uri, token = _resolve_registration(config_env, config_file)
    try:
        result = read_client(registration_client_uri=uri, registration_access_token=token)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(result, indent=2))


def cmd_auth_client_update(
    *,
    config_env: Annotated[str | None, cyclopts.Parameter(help=_CONFIG_ENV_HELP)] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    redirect_uri: Annotated[str | None, cyclopts.Parameter(help=_REDIRECT_URI_HELP)] = None,
    client_name: Annotated[str | None, cyclopts.Parameter(help=_CLIENT_NAME_HELP)] = None,
    scope: Annotated[str | None, cyclopts.Parameter(help=_SCOPE_HELP)] = None,
) -> None:
    """Correct an OAuth client's registration, e.g. after registering it with a wrong redirect URI.

    Only the OAuth client is changed. A webapp's B-Fabric application record holds the same URL in
    its ``weburl``, which this does not touch — fix that with 'bfabric-cli api update application'.
    """
    env_name, uri, token = _resolve_registration(config_env, config_file)
    if redirect_uri is None and client_name is None and scope is None:
        print("Error: Nothing to update. Pass --redirect-uri, --client-name and/or --scope.", file=sys.stderr)
        raise SystemExit(1)

    try:
        # RFC 7592 PUT replaces the metadata document, so start from the server's current
        # version and overlay only what was asked for.
        metadata = dict(read_client(registration_client_uri=uri, registration_access_token=token))
        if redirect_uri is not None:
            metadata["redirect_uris"] = [redirect_uri]
        if client_name is not None:
            metadata["client_name"] = client_name
        if scope is not None:
            metadata["scope"] = scope
        result = update_client(
            registration_client_uri=uri,
            registration_access_token=token,
            metadata=metadata,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    # Before printing: a rotated token is only useful if it is stored, and the print is noisy enough
    # that a reader could miss it.
    _persist_rotated_credentials(result, env_name, config_file)
    print(json.dumps(result, indent=2))


def cmd_auth_client_delete(
    *,
    config_env: Annotated[str | None, cyclopts.Parameter(help=_CONFIG_ENV_HELP)] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    no_confirm: Annotated[bool, cyclopts.Parameter(help=_NO_CONFIRM_HELP, negative=())] = False,
) -> None:
    """Delete an OAuth client from the server, revoking it for good.

    The client stops being able to obtain tokens and cannot be restored — a replacement has to be
    registered from scratch. The environment is kept, minus the credentials that just died with it.
    """
    env_name, uri, token = _resolve_registration(config_env, config_file)
    if not no_confirm:
        if not is_interactive():
            print(
                f"Refusing to delete the OAuth client of '{env_name}' without confirmation; "
                f"pass --no-confirm to proceed.",
                file=sys.stderr,
            )
            return
        if not confirm(
            f"Delete the OAuth client registered for '{env_name}'? This cannot be undone and any "
            f"script using it stops authenticating."
        ):
            print("No changes made.")
            return

    try:
        delete_client(registration_client_uri=uri, registration_access_token=token)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    # Only after the server confirmed: the credentials are dead, and leaving them would let a later
    # command fail with a confusing 401 instead of "not configured".
    # auth_method goes too: a client_credentials environment without its secret cannot authenticate,
    # and leaving it would claim an auth method the environment can no longer perform.
    dead: dict[str, object] = dict.fromkeys(("client_secret", "registration_access_token", "registration_client_uri"))
    if read_environment_auth_keys(config_file, env_name).get("auth_method") == "client_credentials":
        dead["auth_method"] = None
    write_environment_to_config(config_file, env_name, dead, auth="merge", set_default=False)
    print(f"Deleted the OAuth client registered for '{env_name}'.")
