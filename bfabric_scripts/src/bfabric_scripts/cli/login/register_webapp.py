"""Register an OAuth webapp with B-Fabric: create OAuth client + application."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric_scripts.cli.login._constants import DEFAULT_REGISTRATION_SCOPE


def cmd_login_register_webapp(
    app_name: Annotated[str, cyclopts.Parameter(help="Human-readable name for the webapp.")],
    web_url: Annotated[str, cyclopts.Parameter(help="The webapp URL (used as redirect URI and application weburl).")],
    *,
    config_env: Annotated[str | None, cyclopts.Parameter(help="Config environment to use.")] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    service_user: Annotated[
        str | None, cyclopts.Parameter(help="Service user login (enables client_credentials grant).")
    ] = None,
    scope: Annotated[str, cyclopts.Parameter(help="OAuth scope.")] = DEFAULT_REGISTRATION_SCOPE,
    application_id: Annotated[
        int | None, cyclopts.Parameter(help="Existing application ID to update (omit to create new).")
    ] = None,
    technology_id: Annotated[int | None, cyclopts.Parameter(help="Technology ID for the application.")] = None,
    description: Annotated[str | None, cyclopts.Parameter(help="Application description.")] = None,
) -> None:
    """Register a new OAuth webapp: create OAuth client and B-Fabric application.

    Uses the current config environment's credentials for both the OAuth
    registration endpoint (Bearer token) and the SOAP application save.
    """
    from bfabric import Bfabric
    from bfabric._oauth.registration import register_webapp

    try:
        client = Bfabric.connect(
            config_file_path=config_file,
            config_file_env=config_env or "default",
        )
    except Exception as e:
        print(f"Error: Could not connect to B-Fabric: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    bearer_token = client.auth.password.get_secret_value()

    try:
        result = register_webapp(
            client=client,
            token=bearer_token,
            app_name=app_name,
            web_url=web_url,
            service_user=service_user,
            scope=scope,
            application_id=application_id,
            technology_id=technology_id,
            description=description,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    oauth_info = result["oauth"]
    print(json.dumps(oauth_info, indent=2))
    print(
        f"\nApplication saved. OAuth client id={oauth_info['id']}, client_id={oauth_info['client_id']}",
        file=sys.stderr,
    )
