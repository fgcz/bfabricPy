"""Register an OAuth client with B-Fabric (RFC 7591)."""

from __future__ import annotations

import getpass
import json
import sys
from typing import Annotated

import cyclopts

from bfabric._oauth.registration import register_client


def cmd_login_register(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    client_name: Annotated[str, cyclopts.Parameter(help="Human-readable name for the client.")],
    redirect_uri: Annotated[str, cyclopts.Parameter(help="OAuth redirect URI for the client.")],
    *,
    token: Annotated[str | None, cyclopts.Parameter(help="Employee Bearer token (prompted if omitted).")] = None,
    service_user: Annotated[str | None, cyclopts.Parameter(help="Service user login (enables client_credentials grant).")] = None,
    scope: Annotated[str | None, cyclopts.Parameter(help="OAuth scope (defaults to server default).")] = None,
) -> None:
    """Register a new OAuth client with the B-Fabric server."""
    if token is None:
        token = getpass.getpass("Employee Bearer token: ")
    else:
        print("Warning: passing secrets via CLI flags is insecure (visible in ps, shell history).", file=sys.stderr)
    try:
        result = register_client(
            base_url=base_url,
            token=token,
            client_name=client_name,
            redirect_uri=redirect_uri,
            service_user=service_user,
            scope=scope,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(result, indent=2))
