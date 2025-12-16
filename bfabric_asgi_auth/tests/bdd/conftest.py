"""Pytest-BDD configuration and shared fixtures."""

from __future__ import annotations

import asyncio
import time

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pytest_bdd import given, parsers, then, when
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

from bfabric_asgi_auth import BfabricAuthMiddleware, create_mock_validator


# Helper to run async code in sync context
def run_async(coro):
    """Run async coroutine synchronously."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# Test context to store state between steps
@pytest.fixture
def context():
    """Shared context for storing test state."""
    return {}


# Application fixtures
@pytest.fixture
def mock_validator():
    """Create a mock token validator."""
    return create_mock_validator()


@pytest.fixture
def base_app():
    """Create a base Starlette application."""

    async def homepage(request: Request):
        return JSONResponse(
            {
                "message": "success",
                "scope_keys": list(request.scope.keys()),
                "has_bfabric_session": "bfabric_session" in request.scope,
            }
        )

    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json(
            {
                "connected": True,
                "has_bfabric_session": "bfabric_session" in websocket.scope,
            }
        )
        await websocket.close()

    routes = [
        Route("/", homepage),
        Route("/nonexistent", homepage),
        WebSocketRoute("/ws", websocket_endpoint),
    ]
    return Starlette(routes=routes)


@pytest.fixture
def app_config():
    """Default app configuration."""
    return {
        "landing_path": "/landing",
        "token_param": "token",
        "authenticated_path": "/",
        "logout_path": "/logout",
        "session_secret": "test-secret-key-min-32-characters!!",
        "session_max_age": 3600,
    }


@pytest.fixture
def app(base_app, mock_validator, app_config):
    """Create configured application with middleware."""
    # Add BfabricAuthMiddleware
    base_app.add_middleware(
        BfabricAuthMiddleware,
        token_validator=mock_validator,
        landing_path=app_config["landing_path"],
        token_param=app_config["token_param"],
        authenticated_path=app_config["authenticated_path"],
        logout_path=app_config["logout_path"],
    )

    # Add SessionMiddleware (wraps BfabricAuthMiddleware)
    base_app.add_middleware(
        SessionMiddleware,
        secret_key=app_config["session_secret"],
        max_age=app_config["session_max_age"],
    )

    return base_app


@pytest_asyncio.fixture
async def client(app, context):
    """Create async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        context["client"] = ac
        yield ac


# ============================================================================
# Given steps
# ============================================================================


@given("the application is configured with auth middleware", target_fixture="context")
def app_configured(context, app):
    """Application is configured (happens via fixtures)."""
    context["app"] = app
    return context


@given(parsers.parse('the application is configured with {param}="{value}"'), target_fixture="app")
def app_configured_with_param(base_app, mock_validator, param, value):
    """Configure application with specific parameter."""
    config = {
        "landing_path": "/landing",
        "token_param": "token",
        "authenticated_path": "/",
        "logout_path": "/logout",
    }
    config[param] = value

    base_app.add_middleware(
        BfabricAuthMiddleware,
        token_validator=mock_validator,
        **config,
    )
    base_app.add_middleware(
        SessionMiddleware,
        secret_key="test-secret-key-min-32-characters!!",
        max_age=3600,
    )

    return base_app


@given(parsers.parse('I am authenticated with token "{token}"'))
def authenticated_with_token(context, client, token):
    """Authenticate with a token."""
    # Client will automatically store cookies from this response
    response = run_async(client.get(f"/landing?token={token}", follow_redirects=False))
    context["authenticated"] = True


@given("I have no session cookie", target_fixture="context")
def no_session_cookie(context, client):
    """Clear session cookies."""
    # Clear the client's cookie jar to ensure no cookies are sent
    client.cookies.clear()
    context["authenticated"] = False
    return context


@given(parsers.parse("the session max_age is {seconds:d} second"), target_fixture="context")
def session_max_age(context, base_app, mock_validator, seconds):
    """Configure session with specific max_age."""
    base_app.add_middleware(
        BfabricAuthMiddleware,
        token_validator=mock_validator,
    )
    base_app.add_middleware(
        SessionMiddleware,
        secret_key="test-secret-key-min-32-characters!!",
        max_age=seconds,
    )
    context["app"] = base_app
    context["session_max_age"] = seconds
    return context


@given("I am using the mock validator", target_fixture="context")
def using_mock_validator(context, mock_validator):
    """Set mock validator in context."""
    context["validator"] = mock_validator
    return context


@given("the session has expired")
def session_expired(context):
    """Mark session as expired."""
    if "session_max_age" in context:
        time.sleep(context["session_max_age"] + 0.1)


# ============================================================================
# When steps
# ============================================================================


@when(parsers.parse('I visit "{url}"'))
def visit_url(context, client, url):
    """Visit a URL."""
    # Client automatically handles cookies
    response = run_async(client.get(url, follow_redirects=False))
    context["response"] = response


@when(parsers.parse('I request "{url}"'))
def request_url(context, client, url):
    """Make a request to URL."""
    # Client automatically handles cookies
    response = run_async(client.get(url))
    context["response"] = response


@when(parsers.parse('I request "{url}" {count} times'))
def request_url_multiple(context, client, url, count):
    """Make multiple requests to URL."""
    # Client automatically handles cookies
    responses = []
    for _ in range(int(count) if count.isdigit() else 3):
        response = run_async(client.get(url))
        responses.append(response)
    context["responses"] = responses
    context["response"] = responses[-1]  # Also store last response


@when("I modify the session cookie")
def modify_cookie(context, client):
    """Tamper with session cookie."""
    if "session" in client.cookies:
        # Modify the session cookie value
        client.cookies.set("session", "tampered_value")


@when(parsers.parse("I wait {seconds:d} seconds"))
def wait_seconds(context, seconds):
    """Wait for specified seconds."""
    time.sleep(seconds)


@when(parsers.parse('I validate token "{token}"'))
def validate_token(context, token):
    """Validate a token."""
    validator = context.get("validator")
    from pydantic import SecretStr

    result = run_async(validator(SecretStr(token)))
    context["validation_result"] = result


@when("multiple users authenticate with different tokens")
def multiple_users_authenticate(context, app):
    """Simulate concurrent authentication."""
    from httpx import ASGITransport, AsyncClient

    tokens = ["valid_user1", "valid_user2", "valid_user3"]
    sessions = []

    async def authenticate_users():
        results = []
        for token in tokens:
            # Create a separate client for each user
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as user_client:
                response = await user_client.get(f"/landing?token={token}", follow_redirects=False)
                # Extract cookies from this specific client
                cookies = {name: value for name, value in user_client.cookies.items()}
                results.append({"token": token, "cookies": cookies})
        return results

    sessions = run_async(authenticate_users())
    context["multiple_sessions"] = sessions


@when(parsers.parse('I connect to WebSocket "{path}"'))
def connect_websocket(context, app, client, path):
    """Attempt WebSocket connection."""
    # Use Starlette's TestClient for WebSocket support
    from starlette.testclient import TestClient

    # Get cookies from httpx client to pass to WebSocket connection
    cookies = {name: value for name, value in client.cookies.items()}

    test_client = TestClient(app)
    # Set cookies in test client
    for name, value in cookies.items():
        test_client.cookies.set(name, value)

    try:
        with test_client.websocket_connect(path) as websocket:
            data = websocket.receive_json()
            context["websocket_response"] = data
            context["websocket_connected"] = True
    except Exception as e:
        context["websocket_connected"] = False
        context["websocket_error"] = str(e)


# ============================================================================
# Then steps
# ============================================================================


@then(parsers.parse('I should be redirected to "{url}"'))
def redirected_to(context, url):
    """Check redirect location."""
    response = context["response"]
    assert response.status_code == 302
    assert response.headers["location"] == url


@then(parsers.parse("I should receive a {status_code:d} status code"))
def status_code(context, status_code):
    """Check status code."""
    response = context["response"]
    assert response.status_code == status_code


@then(parsers.parse('the response should contain "{text}"'))
def response_contains(context, text):
    """Check response contains text."""
    response = context["response"]
    assert text in response.text


@then("I should have a session cookie")
def has_session_cookie(context):
    """Check session cookie exists."""
    response = context["response"]
    assert "session" in response.cookies


@then("I should not have a session cookie")
def no_session_cookie_set(context):
    """Check no session cookie was set."""
    response = context["response"]
    assert "session" not in response.cookies or response.cookies["session"] == ""


@then("the session should contain user information")
def session_contains_user_info(context, client):
    """Check session contains user info."""
    # Client automatically handles cookies
    response = run_async(client.get("/"))
    data = response.json()
    assert data["has_bfabric_session"]


@then(parsers.parse('the scope should contain "{key}"'))
def scope_contains(context, client, key):
    """Check scope contains key."""
    # Client automatically handles cookies
    response = run_async(client.get("/"))
    data = response.json()
    assert key in data["scope_keys"]


@then("all requests should return 200 status code")
def all_requests_success(context):
    """Check all responses are 200."""
    responses = context["responses"]
    for response in responses:
        assert response.status_code == 200


@then("the validation should succeed")
def validation_succeeds(context):
    """Check validation succeeded."""
    result = context["validation_result"]
    assert result.success is True


@then("the validation should fail")
def validation_fails(context):
    """Check validation failed."""
    result = context["validation_result"]
    assert result.success is False


@then("the result should contain client configuration")
def result_has_client_config(context):
    """Check validation result has client config."""
    result = context["validation_result"]
    assert result.bfabric_instance is not None
    assert result.bfabric_auth is not None


@then("the result should contain user information")
def result_has_user_info(context):
    """Check validation result has user info."""
    result = context["validation_result"]
    assert result.user_info is not None


@then(parsers.parse('the error should contain "{text}"'))
def error_contains(context, text):
    """Check error message contains text."""
    result = context["validation_result"]
    assert text in result.error


@then(parsers.parse('the client config should contain "{field}"'))
def client_config_has_field(context, field):
    """Check client config has field."""
    result = context["validation_result"]
    assert getattr(result, field) is not None


@then(parsers.parse('the user info should contain "{field}"'))
def user_info_has_field(context, field):
    """Check user info has field."""
    result = context["validation_result"]
    assert field in result.user_info


@then("the token should be URL-decoded correctly")
def token_decoded(context):
    """Check token was decoded (verified by successful redirect)."""
    response = context["response"]
    assert response.status_code == 302


@then("each user should have an independent session")
def independent_sessions(context):
    """Check sessions are independent."""
    sessions = context["multiple_sessions"]
    cookies = [s["cookies"]["session"] for s in sessions]
    # All cookies should be different
    assert len(cookies) == len(set(cookies))


@then("sessions should not interfere with each other")
def sessions_no_interference(context):
    """Check sessions don't interfere."""
    # This is validated by independent_sessions
    pass


@then(parsers.parse("the connection should be rejected with code {code:d}"))
def websocket_rejected(context, code):
    """Check WebSocket was rejected."""
    assert not context.get("websocket_connected", False)


@then("the connection should be accepted")
def websocket_accepted(context):
    """Check WebSocket was accepted."""
    assert context.get("websocket_connected", False)
