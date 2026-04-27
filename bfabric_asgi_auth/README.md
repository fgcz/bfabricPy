# B-Fabric ASGI Authentication Middleware

ASGI middleware for authenticating B-Fabric web applications using cookie-based sessions.

Integrates any ASGI application as a B-Fabric web application, simply by adding the middleware to your application.
Supports HTTP(S) and WebSocket out of the box.

## Example

TODO: To be linked here later, we have a few internal examples so far.

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

### Obtaining the token data

- In most cases, you should define a `on_success` callback to handle the token data with your application logic.
- The `bfabric_instance`, `bfabric_auth_login` and `bfabric_auth_password` are available in the `bfabric_session` key of `session`.

### Session management

In many cases, a user may have multiple sessions of a particular web app open.

Your application is responsible for correctly behaving in this scenario, which is why if it is sensitive to the value of `TokenData`
you should encode this information most likely in the path of the session witth a `on_success` callback.

The middleware currently has the behavior, that if the session is already authenticated but with a different user or B-Fabric instance, the session
will be evicted. This behavior can be changed.

### Visible errors

If you want to raise an error to the browser from a hook (e.g. inside `on_success`), raise a `VisibleException` with a structured `error_type`. The middleware preserves the type so the renderer can pick the right copy:

```python
from bfabric_asgi_auth import VisibleException


class Hooks:
    async def on_success(self, session, token_data):
        try:
            workunit = await load_workunit(token_data.entity_id)
        except InvalidZipFile as e:
            raise VisibleException(
                str(e), status_code=500, error_type="invalid_zip"
            ) from e
```

Bare `Exception`s raised in hooks are rendered as a generic 500 — wrap them in `VisibleException` for tailored copy.

### Customizing copy and branding

The bundled `HTMLRenderer` ships with B-Fabric branding defaults (wordmark, accent colour, return-to-B-Fabric footer). Apps inject their own copy via two callables:

```python
from bfabric_asgi_auth import HTMLRenderer

copy = {
    "token_expired": "Your B-Fabric session expired — return to B-Fabric and click View Results.",
    "token_invalid": "B-Fabric token validation failed. Please contact support.",
    "invalid_zip": "The workunit's zip file is corrupted or empty.",
}

renderer = HTMLRenderer(
    page_title="B-Fabric Zip Browser",
    bfabric_url="https://fgcz-bfabric.uzh.ch/bfabric/",
    error_message=lambda error_type, default: copy.get(error_type, default),
)
```

`error_type` strings emitted by the middleware: `unauthorized`, `missing_token`, `token_expired`, `token_invalid`, `token_network`, `token_unknown`, `invalid_session`, `callback_error`, `unknown`. Apps can register additional types via `VisibleException`.

To opt out of B-Fabric branding (e.g. for a non-B-Fabric tenant), pass `bfabric_branding=False`.

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
