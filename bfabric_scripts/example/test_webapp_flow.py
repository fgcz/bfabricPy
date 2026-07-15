#!/usr/bin/env python3
"""Interactive integration test for the full webapp OAuth flow.

Run with:
    python -m bfabric_scripts.example.test_webapp_flow

This script:
1. Registers a new OAuth client + B-Fabric application via ``register_webapp``
2. Starts a local HTTP server that acts as the webapp
3. Prints a URL for you to launch the application from B-Fabric
4. Waits for B-Fabric to redirect back with a ``jwt`` parameter
5. Exchanges the launch token via ``WebappClient.create()``
6. Reads something from B-Fabric with the user and service clients
7. Cleans up (deletes the application)
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from bfabric import Bfabric
from bfabric._oauth.registration import register_webapp
from bfabric._oauth.webapp_client import WebappClient
from bfabric.entities.core.uri import EntityUri
from bfabric_scripts.cli.login._constants import DEFAULT_OAUTH_SCOPE

PORT = 19876
REDIRECT_PATH = "/callback"


def main() -> None:
    config_env = None
    if len(sys.argv) > 1:
        config_env = sys.argv[1]

    print("=== Webapp OAuth Flow Integration Test ===\n")

    # Connect to B-Fabric
    print("Connecting to B-Fabric...")
    client = Bfabric.connect(config_file_env=config_env)
    base_url = client.config.base_url.rstrip("/")
    bearer_token = client.auth.password.get_secret_value()
    print(f"  base_url: {base_url}")

    # Register webapp
    web_url = f"http://localhost:{PORT}{REDIRECT_PATH}"
    app_name = f"integration-test-webapp-{PORT}"

    print(f"\nRegistering webapp '{app_name}'...")
    result = register_webapp(
        client=client,
        token=bearer_token,
        app_name=app_name,
        web_url=web_url,
        service_user="itfeeder",
        scope=DEFAULT_OAUTH_SCOPE,
        hidden=True,
    )
    oauth_info = result["oauth"]
    app_result = result["application"]

    oauth_client_id = str(oauth_info["client_id"])
    oauth_client_secret = str(oauth_info["client_secret"])
    oauth_internal_id = oauth_info["id"]

    # Extract the application ID from the save result
    if len(app_result) > 0:
        app_id = int(app_result[0]["id"])  # pyright: ignore[reportArgumentType]
    else:
        app_id = None

    print(f"  OAuth client_id: {oauth_client_id}")
    print(f"  OAuth internal id: {oauth_internal_id}")
    print(f"  Application ID: {app_id}")
    print(f"  client_secret: {oauth_client_secret[:8]}...")

    if app_id is None:
        print("  Application registration failed.")
        return

    # Prepare to receive the callback
    received_token: dict[str, str | None] = {"jwt": None}
    server_ready = threading.Event()
    request_received = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != REDIRECT_PATH:
                self.send_response(404)
                self.end_headers()
                return

            params = parse_qs(parsed.query)
            jwt_values = params.get("jwt") or params.get("token")
            if jwt_values:
                received_token["jwt"] = jwt_values[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if received_token["jwt"]:
                _ = self.wfile.write(b"<h1>Token received! You can close this tab.</h1>")
            else:
                _ = self.wfile.write(b"<h1>No JWT found in URL parameters.</h1>")
                _ = self.wfile.write(f"<pre>query: {parsed.query}</pre>".encode())
            request_received.set()

        def log_message(self, format: str, *args: object) -> None:  # pyright: ignore[reportImplicitOverride]
            pass  # Suppress request logging

    server = HTTPServer(("", PORT), CallbackHandler)

    def serve() -> None:
        server_ready.set()
        server.handle_request()  # Handle exactly one request

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()
    _ = server_ready.wait()

    print(f"\n{'=' * 60}")
    print(f"Local server listening on http://localhost:{PORT}")
    print(f"\nNow go to B-Fabric and launch application ID={app_id}:")
    print(f"  {EntityUri.from_components(base_url, 'application', app_id)}")
    print(f"\nOr, if your app is launched from a workunit, run it from there.")
    print(f"B-Fabric will redirect to: {web_url}?jwt=...")
    print(f"{'=' * 60}\n")
    print("Waiting for callback...")

    _ = request_received.wait(timeout=300)
    server.server_close()

    jwt = received_token["jwt"]
    if not jwt:
        print("\nERROR: No JWT received (timeout or missing parameter).", file=sys.stderr)
        _cleanup(client, app_id)
        raise SystemExit(1)

    print(f"\nReceived launch token: {jwt[:40]}...")

    # Exchange the token
    print("\nExchanging launch token via WebappClient.create()...")
    try:
        wc = WebappClient.create(
            base_url=base_url,
            launch_token=jwt,
            client_id=oauth_client_id,
            client_secret=oauth_client_secret,
            scope=DEFAULT_OAUTH_SCOPE,
        )
    except Exception as e:
        print(f"\nERROR: Token exchange failed: {e}", file=sys.stderr)
        _cleanup(client, app_id)
        raise SystemExit(1) from None

    print(f"  context.entity_id: {wc.context.entity_id}")
    print(f"  context.application_id: {wc.context.application_id}")
    print(f"  context.subject: {wc.context.subject}")
    print(f"  context.job_id: {wc.context.job_id}")

    # Test user client
    print("\nTesting user client (reading user info)...")
    try:
        user_result = wc.user.read("user", {"login": wc.context.subject}, max_results=1)
        print(f"  User read OK: {json.dumps(user_result[0], indent=2, default=str)[:200]}...")
    except Exception as e:
        print(f"  User read FAILED: {e}")

    # Test service client
    print("\nTesting service client (reading application)...")
    try:
        if wc.context.application_id:
            svc_result = wc.service.read("application", {"id": wc.context.application_id}, max_results=1)
            print(f"  Service read OK: {json.dumps(svc_result[0], indent=2, default=str)[:200]}...")
        else:
            print("  Skipped (no application_id in context)")
    except Exception as e:
        print(f"  Service read FAILED: {e}")

    print(f"\n{'=' * 60}")
    print("SUCCESS: Full webapp OAuth flow completed!")
    print(f"{'=' * 60}")

    _cleanup(client, app_id)


def _cleanup(client: Bfabric, app_id: int | None) -> None:
    if app_id is None:
        return
    print(f"\nCleaning up: deleting application {app_id}...")
    try:
        _ = client.delete("application", app_id)
        print("  Deleted.")
    except Exception as e:
        print(f"  Cleanup failed (manual deletion may be needed): {e}")


if __name__ == "__main__":
    main()
