# B-Fabric ASGI Authentication Middleware

ASGI middleware for authenticating B-Fabric web applications using cookie-based sessions via OAuth 2.0.

Integrates any ASGI application as a B-Fabric web application, simply by adding the middleware to your application.
Supports HTTP(S) and WebSocket out of the box.

## Example

TODO: To be linked here later, we have a few internal examples so far.

### Token Validators

**Mock validator** (testing):

```python
from bfabric_asgi_auth import create_mock_oauth_validator

token_validator = create_mock_oauth_validator()  # Accepts tokens starting with 'valid_'
```

**OAuth validator** (production):

```python
from bfabric_asgi_auth import (
    create_oauth_validator,
    WebappOAuthSettings,
    OAuthClientCredentials,
)

settings = WebappOAuthSettings(
    base_url="https://fgcz-bfabric.uzh.ch/bfabric",
    credentials=OAuthClientCredentials(
        client_id="your-client-id",
        client_secret="your-client-secret",
    ),
)
token_validator = create_oauth_validator(settings)
```

## Usage

### Authentication Flow

1. User visits `/landing?token=<launch_jwt>` (short-lived JWT from B-Fabric URL)
2. Middleware exchanges the launch JWT for access + refresh tokens (RFC 8693)
3. OAuth session stored in encrypted cookie: `{base_url, token, context}`
4. Redirects to `/` (or `authenticated_path`)
5. All subsequent requests use the session cookie; token is auto-refreshed on expiry

### Middleware setup

```python
from starlette.middleware.sessions import SessionMiddleware
from bfabric_asgi_auth import (
    BfabricAuthMiddleware,
    create_oauth_validator,
    WebappOAuthSettings,
)

app.add_middleware(
    BfabricAuthMiddleware,
    token_validator=create_oauth_validator(settings),
    client_id="your-client-id",  # required: used to rebuild the user client on each request
    client_secret="your-client-secret",
)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SESSION_SECRET_KEY"],
    https_only=True,
    max_age=3600,
)
```

Note: `add_middleware` inserts in reverse order, so `SessionMiddleware` will wrap `BfabricAuthMiddleware`.

### Accessing the authenticated user

```python
from bfabric_asgi_auth import BfabricOAuthUser


async def my_route(request: Request):
    user: BfabricOAuthUser = request.user
    client = user.get_bfabric_client()  # Bfabric instance for this user
    # user.subject — OAuth subject (login)
    # user.base_url — B-Fabric instance URL
    # user.entity_id / entity_class / application_id / job_id — from the launch JWT
```

### Session shape

The `bfabric_session` cookie key contains:

```json
{
  "base_url": "https://fgcz-bfabric.uzh.ch/bfabric",
  "token": {"access_token": "...", "refresh_token": "...", "expires_at": 1234567890},
  "context": {"subject": "alice", "entityId": 42, "entityClassName": "Workunit", ...}
}
```

**Token refresh write-back:** when the Bfabric client silently refreshes the access token during a
request, the new token is written back to the live session dict before `http.response.start`, so the
updated token is persisted to the encrypted cookie automatically.

### Customizing landing behavior

```python
from bfabric_asgi_auth.typing import AuthHooks
from bfabric._oauth.url_token import UrlTokenContext


class MyHooks(AuthHooks):
    async def on_success(self, session: dict, context: UrlTokenContext) -> str | None:
        # Redirect to a job-specific path after login
        if context.job_id:
            return f"/jobs/{context.job_id}"
        return None  # use default authenticated_path
```

### Visible errors

Error handling can be customized with a custom renderer, however before that it would probably be a better use of time to improve the implementation here.
If you want to raise an error to the browser, you should raise a `VisibleException` instance with the error message and status code.

## Security

### Secret Key

**Critical:** Use a strong secret key for SessionMiddleware:

```python
import secrets
from loguru import logger


def _generate_random_secret_key():
    logger.warning(
        "Generating random secret key, cookies will not be persistent across restarts. "
        "To fix this, set SECRET_KEY in your environment or config file.",
    )
    return secrets.token_urlsafe(64)


secret_key = _generate_random_secret_key()
```

- Minimum 32 characters
- Randomly generated
- Never commit to version control
- Different per environment

### Token storage

The full OAuth token (including `refresh_token`) is stored in the **encrypted** session cookie. The
cookie is signed with `SESSION_SECRET_KEY` and encrypted client-side. The `client_secret` is **never**
stored in the session — it lives server-side in the application config.

Because the full token is in the cookie (~4 KB encrypted), it is important to keep the session cookie
max_age reasonably short and rotate `SESSION_SECRET_KEY` periodically.

### Known limitations

- **`aud`/`iss` claims are not validated** — `verify_jwt` is called without `audience` or `issuer`. These
  will be wired once the server-side claims are confirmed against a real B-Fabric instance. OAuth is
  currently in the `experimental` namespace and unverified against a real server.
- **No write-back for WebSocket or post-response-start refreshes** — token refresh write-back only works
  for standard HTTP requests where `http.response.start` has not yet been sent.

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
