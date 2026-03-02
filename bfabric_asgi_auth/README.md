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

Error handling can be customized with a custom renderer, however before that it would probably be a better use of time to improve the implementation here.
If you want to raise an error to the browser, you should raise a `VisibleException` instance with the error mesage and status code.

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
