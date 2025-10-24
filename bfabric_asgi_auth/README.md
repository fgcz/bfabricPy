# Bfabric ASGI Authentication Middleware

ASGI middleware for authenticating Bfabric web applications using URL-based sessions.

## Features

- **URL-based sessions**: Shareable, bookmarkable session URLs
- **Token validation**: Validates Bfabric tokens using `Bfabric.connect_webapp`
- **Session management**: In-memory session store with TTL support
- **State machine**: Tracks session lifecycle (NEW → READY/ERROR)
- **ASGI compliant**: Works with FastAPI, Starlette, and other ASGI frameworks

## Installation

```bash
pip install -e .
```

## Quick Start

### With Mock Validator (Testing)

```python
import fastapi
from bfabric_asgi_auth import (
    BfabricAuthMiddleware,
    SessionStoreMem,
    create_mock_validator,
)

app = fastapi.FastAPI()

# Use mock validator for testing (accepts tokens starting with 'valid_')
token_validator = create_mock_validator()
session_store = SessionStoreMem(default_ttl=3600)

app.add_middleware(
    BfabricAuthMiddleware,
    token_validator=token_validator,
    session_store=session_store,
)


@app.get("/")
async def root(request: fastapi.Request):
    session_data = request.scope.get("session_data", {})
    return {"user": session_data.get("user_info", {}).get("username")}
```

### With Real Bfabric Validator (Production)

```python
from bfabric_asgi_auth import create_bfabric_validator

token_validator = create_bfabric_validator(
    validation_instance_url="https://fgcz-bfabric-test.uzh.ch/bfabric/"
)

app.add_middleware(
    BfabricAuthMiddleware,
    token_validator=token_validator,
    session_store=SessionStoreMem(),
)
```

## How It Works

### Authentication Flow

1. **Landing URL**: User accesses `/landing?token=xyz`

    - Middleware validates token with Bfabric
    - Creates session in memory store
    - Redirects to `/session/{session_id}/`

2. **Session URLs**: User accesses `/session/{session_id}/path`

    - Middleware validates session exists and is READY
    - Attaches session data to request scope
    - Rewrites path (removes `/session/{session_id}` prefix)
    - Passes to main application

3. **Protected Resources**: Application endpoints access session data

    ```python
    @app.get("/data")
    async def get_data(request: fastapi.Request):
        session_data = request.scope.get("session_data", {})
        bfabric_config = request.scope.get("bfabric_connection", {})
        # Use bfabric_config to make authenticated API calls
    ```

### URL Structure

```
/landing?token=xyz           → Landing page (creates session)
/session/{uuid}/             → Root of protected app
/session/{uuid}/data         → Protected endpoint
/session/{uuid}/api/users    → Another protected endpoint
/other                       → Returns 401 Unauthorized
```

## Configuration Options

```python
app.add_middleware(
    BfabricAuthMiddleware,
    token_validator=token_validator,  # Required: Token validator instance
    session_store=session_store,  # Optional: Session store (default: new SessionStoreMem())
    landing_path="/landing",  # Optional: Landing URL path
    session_prefix="/session",  # Optional: Session URL prefix
    token_param="token",  # Optional: Token query parameter name
)
```

## Accessing Session Data

The middleware adds the following to `request.scope`:

- `session_id` (str): The session UUID
- `session_data` (dict): Full session data including:
    - `state`: Session state (NEW, READY, ERROR)
    - `token`: The authentication token
    - `client_config`: Bfabric client configuration (base_url, login, password)
    - `user_info`: User information from token validation
- `bfabric_connection` (dict): Bfabric client config for easy access

## Example Usage

```bash
# Start the example server
uvicorn examples.example_app:app --reload

# Get a session (with mock validator)
curl "http://localhost:8000/landing?token=valid_test123"
# Redirects to: /session/123e4567-e89b-12d3-a456-426614174000/

# Access protected endpoints
curl "http://localhost:8000/session/123e4567-e89b-12d3-a456-426614174000/"
curl "http://localhost:8000/session/123e4567-e89b-12d3-a456-426614174000/data"
```

## Development

See [examples/example_app.py](examples/example_app.py) for a complete working example.

## Session States

Sessions follow a state machine:

- **NEW**: Token validated, session created, not yet initialized
- **READY**: Session initialized and ready for use
- **ERROR**: Session encountered an error during initialization

## Why URL-based Sessions?

URL-based sessions (vs cookie-based) provide:

- **Shareable links**: Users can share specific sessions with colleagues
- **Direct file access**: Links to files remain valid
- **No cookie complexity**: Works across domains and iframes
- **Bookmarkable**: Users can bookmark specific sessions
