# Creating a Client for Server and Webapp Usage

This guide covers how to create a `Bfabric` client for server-side applications and webapps that integrate with B-Fabric,
using token-based authentication.

## Overview

For server and webapp usage, bfabricPy provides token-based authentication methods. These are designed for situations
where:

- You're building a web server or application that integrates with B-Fabric
- Users authenticate via B-Fabric webapp tokens
- You need to validate and restrict which B-Fabric instances tokens can come from
- You're using async web frameworks (e.g., FastAPI, asyncio)
- You need to perform operations on behalf of users

## Token-Based Authentication Methods

### `connect_token()` / `connect_token_async()` - Token Authentication

These methods create a client from a B-Fabric webapp token. They are functionally equivalent:

- `connect_token()` - Synchronous wrapper that runs an event loop internally. Use in synchronous code or outside async contexts.
- `connect_token_async()` - Native async version. Use in async functions or with async web frameworks.

```python
from bfabric import Bfabric
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

# Configure which B-Fabric instances are allowed
settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=[
        "https://fgcz-bfabric.uzh.ch/bfabric/",
        "https://fgcz-bfabric-test.uzh.ch/bfabric/",
    ],
)

# Synchronous usage
token = "your_token_here"
client, token_data = Bfabric.connect_token(token=token, settings=settings)

# Asynchronous usage
# client, token_data = await Bfabric.connect_token_async(token=token, settings=settings)

print(f"Authenticated as: {token_data.user}")
print(f"Token expires: {token_data.token_expires}")
print(f"Token caller: {token_data.caller}")
```

### `from_token_data()` - Create Client from Validated Token

```{warning}
This is a niche use case. Use `connect_token()` or `connect_token_async()` unless you have specific validation requirements.
```

If you need custom token validation logic, you can validate a token yourself and create a client from the `TokenData`:

```python
from bfabric import Bfabric
from bfabric.rest.token_data import get_token_data

# Validate token first
base_url = "https://fgcz-bfabric.uzh.ch/bfabric/"
token = "your_token_here"
token_data = get_token_data(base_url=base_url, token=token)

# Check if the token is from an allowed instance
allowed_instances = ["https://fgcz-bfabric.uzh.ch/bfabric/"]
if token_data.caller not in allowed_instances:
    raise ValueError(f"Token from {token_data.caller} is not allowed")

# Create client
client = Bfabric.from_token_data(token_data)
```

## Configuration

### TokenValidationSettings

The `TokenValidationSettings` class configures which B-Fabric instances are allowed to issue tokens for your application.

```python
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=[
        "https://fgcz-bfabric.uzh.ch/bfabric/",
        "https://fgcz-bfabric-test.uzh.ch/bfabric/",
    ],
)
```

**Parameters:**

- **`validation_bfabric_instance`** (str): The B-Fabric instance to use for token validation. Must be one of the supported instances.
- **`supported_bfabric_instances`** (list[str]): List of B-Fabric instance URLs that are allowed to issue tokens.

```{important}
The `validation_bfabric_instance` must be included in `supported_bfabric_instances`. This is enforced at initialization.
```

### WebappIntegrationSettings

The `WebappIntegrationSettings` class extends `TokenValidationSettings` with `feeder_user_credentials`. Use this when your webapp needs to create or update entities on behalf of users using a privileged service account.

```python
from bfabric.experimental.webapp_integration_settings import WebappIntegrationSettings
from bfabric.config import BfabricAuth

settings = WebappIntegrationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=["https://fgcz-bfabric.uzh.ch/bfabric/"],
    feeder_user_credentials={
        "https://fgcz-bfabric.uzh.ch/bfabric/": BfabricAuth(
            login="feeder_user", password="feeder_user_password"
        ),
    },
)
```

**Parameters:**

- Inherits all parameters from `TokenValidationSettings`
- **`feeder_user_credentials`** (dict[str, BfabricAuth]): Mapping of B-Fabric instance URLs to credentials with permission to create/update entities. All instance keys must be in `supported_bfabric_instances`.

```{note}
Feeder user credentials are typically used when the authenticated user lacks permission to perform certain operations, but a privileged service account does.
```

## Security Best Practices

### Restrict Token Instances

Always restrict `supported_bfabric_instances` to only the instances you trust:

```python
settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=[
        "https://fgcz-bfabric.uzh.ch/bfabric/",  # Only allow production
        # "https://fgcz-bfabric-test.uzh.ch/bfabric/",  # Commented out to prevent test tokens
    ],
)
```

### Check Token Expiration

Verify tokens haven't expired in your application logic:

```python
from datetime import datetime, timezone

client, token_data = Bfabric.connect_token(token=token, settings=settings)

if token_data.token_expires < datetime.now(timezone.utc):
    raise ValueError("Token has expired")
```

### Verify Web Service Permissions

Check if the authenticated user has web service permissions:

```python
if not token_data.web_service_user:
    raise PermissionError("User does not have web service permissions")
```

### Use Secrets for Tokens

For additional security, use `pydantic.SecretStr` when handling tokens:

```python
from pydantic import SecretStr

secret_token = SecretStr(request_token)
client, token_data = Bfabric.connect_token(token=secret_token, settings=settings)
```

## Working with Token Data

When you create a client using token-based methods, you receive both a `Bfabric` client and `TokenData` object:

```python
client, token_data = Bfabric.connect_token(token=token, settings=settings)

# Token data contains useful information
print(f"User: {token_data.user}")
print(f"Application ID: {token_data.application_id}")
print(f"Entity: {token_data.entity_class}#{token_data.entity_id}")
print(f"Job ID: {token_data.job_id}")
print(f"Expires: {token_data.token_expires}")
print(f"Web service user: {token_data.web_service_user}")
print(f"Caller instance: {token_data.caller}")

# Load the entity associated with the token
entity = token_data.load_entity(client=client)
```
