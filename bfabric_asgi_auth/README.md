# B-Fabric ASGI Authentication Middleware

ASGI middleware for authenticating B-Fabric web applications using cookie-based sessions.

Integrates any ASGI application with B-Fabric, simply by adding the middleware to your application.
Supports HTTP(S) and WebSocket out of the box.

## Features

- Cookie-based sessions using Starlette's SessionMiddleware
- Token validation via `Bfabric.connect_webapp`
- Built-in logout endpoint
- WebSocket authentication support
- ASGI compliant (works with FastAPI, Starlette, etc.)

## Installation

```bash
pip install -e .
```

## Quick Start

```python
import fastapi
from starlette.middleware.sessions import SessionMiddleware
from bfabric_asgi_auth import BfabricAuthMiddleware, create_mock_validator

app = fastapi.FastAPI()
token_validator = create_mock_validator()

# IMPORTANT: Add BfabricAuthMiddleware FIRST, then SessionMiddleware
# (add_middleware works in reverse order)
app.add_middleware(BfabricAuthMiddleware, token_validator=token_validator)
app.add_middleware(
    SessionMiddleware, secret_key="your-secret-key-min-32-chars!!", max_age=3600
)


@app.get("/")
async def root(request: fastapi.Request):
    session_data = request.scope.get("bfabric_session", {})
    return {"user": session_data.get("user_info", {}).get("username")}
```

## Configuration

**Middleware order is critical!** Add in this sequence:

```python
# 1. Add BfabricAuthMiddleware FIRST
app.add_middleware(
    BfabricAuthMiddleware,
    token_validator=token_validator,  # Required
    landing_path="/landing",  # Optional (default: /landing)
    token_param="token",  # Optional (default: token)
    authenticated_path="/",  # Optional (default: /)
    logout_path="/logout",  # Optional (default: /logout)
)

# 2. Add SessionMiddleware LAST (wraps BfabricAuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",  # Required: min 32 chars, keep secret!
    max_age=3600,  # Optional: session timeout in seconds
    https_only=False,  # Optional: set True in production
)
```

### Token Validators

**Mock validator** (testing):

```python
from bfabric_asgi_auth import create_mock_validator

token_validator = create_mock_validator()  # Accepts tokens starting with 'valid_'
```

**Bfabric validator** (production):

```python
from bfabric_asgi_auth import create_bfabric_validator

token_validator = create_bfabric_validator(
    validation_instance_url="https://fgcz-bfabric-test.uzh.ch/bfabric/"
)
```

## Usage

### Authentication Flow

1. User visits `/landing?token=xyz`
2. Middleware validates token with Bfabric
3. Session created in encrypted cookie
4. Redirects to `/` (or `authenticated_path`)
5. All subsequent requests use the session cookie

### Accessing Session Data

```python
@app.get("/data")
async def get_data(request: fastapi.Request):
    session_data = request.scope.get("bfabric_session", {})
    bfabric_config = request.scope.get("bfabric_connection", {})

    return {
        "user_info": session_data.get("user_info"),
        "bfabric_url": bfabric_config.get("base_url"),
    }
```

Available in `request.scope`:

- `bfabric_session`: Full session data (client_config, user_info)
- `bfabric_connection`: Bfabric client config (base_url, login, password)

### Example Commands

```bash
# Start server
uvicorn examples.example_app:app --reload

# Login (creates session cookie)
curl -c cookies.txt -L "http://localhost:8000/landing?token=valid_test123"

# Access protected endpoints
curl -b cookies.txt "http://localhost:8000/"
curl -b cookies.txt "http://localhost:8000/data"

# Logout
curl -b cookies.txt "http://localhost:8000/logout"
```

## Security

### Secret Key

**Critical:** Use a strong secret key for SessionMiddleware:

```python
import secrets

secret_key = secrets.token_hex(32)  # Generate 64-char hex string
```

- Minimum 32 characters
- Randomly generated
- Never commit to version control
- Different per environment

### Production Settings

```python
import os

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SESSION_SECRET_KEY"],
    https_only=True,  # Require HTTPS
    max_age=3600,
)
```

## Migration from URL-based Sessions

Previous version used URL-based sessions (`/session/{uuid}/path`). Key changes:

### Before

```python
from bfabric_asgi_auth import SessionStoreMem

session_store = SessionStoreMem(default_ttl=3600)
app.add_middleware(BfabricAuthMiddleware, session_store=session_store, ...)
# URLs: /session/123e4567-e89b-12d3-a456-426614174000/data
```

### After

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(BfabricAuthMiddleware, ...)  # First
app.add_middleware(SessionMiddleware, secret_key="...", max_age=3600)  # Last
# URLs: /data (with session cookie)
```

### Changes

- ✅ Simpler code (no custom session store)
- ✅ Standard Starlette patterns
- ✅ Built-in logout at `/logout`
- ❌ No URL shareability (cookies are per-browser)
- Session data access: `request.scope["bfabric_session"]` (unchanged)

See [examples/example_app.py](examples/example_app.py) for complete examples.
