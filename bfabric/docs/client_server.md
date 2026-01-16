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

### `Bfabric.connect_token()` - Synchronous Token Authentication

Use this method for synchronous code or when not using an async framework:

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

# Create client from token received from B-Fabric webapp
token = "your_token_here"
client, token_data = Bfabric.connect_token(token=token, settings=settings)

print(f"Authenticated as: {token_data.user}")
print(f"Token expires: {token_data.token_expires}")
print(f"Token caller: {token_data.caller}")
```

### `Bfabric.connect_token_async()` - Asynchronous Token Authentication

Use this method when working with async code or frameworks:

```python
import asyncio
from bfabric import Bfabric
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings


async def handle_webapp_request(token: str):
    settings = TokenValidationSettings(
        validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
        supported_bfabric_instances=["https://fgcz-bfabric.uzh.ch/bfabric/"],
    )

    client, token_data = await Bfabric.connect_token_async(
        token=token, settings=settings
    )
    return client, token_data


# Usage in an async web framework
client, token_data = await handle_webapp_request(request_token)
```

### `Bfabric.from_token_data()` - Create Client from Validated Token

If you've already validated a token (e.g., using your own validation logic), you can create a client directly from the
`TokenData`:

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

```{note}
Using `connect_token()` or `connect_token_async()` is recommended over `from_token_data()` because they include
built-in validation through `TokenValidationSettings`.
```

## Security Configuration

### TokenValidationSettings

The `TokenValidationSettings` class is used to configure which B-Fabric instances are allowed to issue tokens for your
application. This provides an important security layer by preventing tokens from unauthorized instances.

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

- **`validation_bfabric_instance`** (str): The B-Fabric instance to use for token validation. Must be one of the
    supported instances.
- **`supported_bfabric_instances`** (list\[str\]): List of B-Fabric instance URLs that are allowed to issue tokens. If a
    token originates from an instance not in this list, validation will fail.

```{important}
The `validation_bfabric_instance` must be included in `supported_bfabric_instances`. This is enforced at
initialization.
```

### WebappIntegrationSettings

The `WebappIntegrationSettings` class extends `TokenValidationSettings` with `feeder_user_credentials`. This is useful
when your webapp needs to create or update entities on behalf of users, using a "feeder" user with elevated permissions.

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
- **`feeder_user_credentials`** (dict\[str, BfabricAuth\]): A dictionary mapping B-Fabric instance URLs to credentials that
    have permission to create/update entities. All instance keys must be in `supported_bfabric_instances`.

```{note}
Feeder user credentials are typically used when the authenticated user lacks permission to perform certain operations,
but a privileged service account does.
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

## Security Considerations

### Token Validation

Always validate tokens and restrict to known instances:

```python
settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=[
        "https://fgcz-bfabric.uzh.ch/bfabric/",  # Only allow production
        # "https://fgcz-bfabric-test.uzh.ch/bfabric/",  # Commented out to prevent test tokens
    ],
)
```

### Token Expiration

Check token expiration in your application logic:

```python
from datetime import datetime, timezone

client, token_data = Bfabric.connect_token(token=token, settings=settings)

if token_data.token_expires < datetime.now(timezone.utc):
    raise ValueError("Token has expired")
```

### Web Service User Permissions

The `web_service_user` field indicates whether the authenticated user has web service permissions:

```python
if not token_data.web_service_user:
    raise PermissionError("User does not have web service permissions")
```

### Using Secrets for Tokens

For additional security, use `pydantic.SecretStr` when handling tokens in your code:

```python
from pydantic import SecretStr

secret_token = SecretStr(request_token)
client, token_data = Bfabric.connect_token(token=secret_token, settings=settings)
```

## Example: FastAPI Webapp Integration

Here's a complete example of integrating with FastAPI:

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from bfabric import Bfabric
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

app = FastAPI()

# Configure security settings
settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=["https://fgcz-bfabric.uzh.ch/bfabric/"],
)


class TokenRequest(BaseModel):
    token: str


@app.post("/process")
async def process_request(request: TokenRequest):
    try:
        # Create client from token (async)
        client, token_data = await Bfabric.connect_token_async(
            token=request.token, settings=settings
        )

        # Use the client to perform operations
        samples = client.read(endpoint="sample", obj={"id": token_data.entity_id})

        return {"user": token_data.user, "samples": samples.to_list()}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Comparison: Scripted vs Server Usage

| Feature                  | Interactive/Scripted (`Bfabric.connect()`) | Server/Webapp (`Bfabric.connect_token()`) |
| ------------------------ | ------------------------------------------ | ----------------------------------------- |
| **Authentication**       | Config file credentials                    | Token from B-Fabric webapp                |
| **User Identity**        | Fixed (from config)                        | Dynamic (from token)                      |
| **Use Case**             | Scripts, local tools                       | Web servers, webapps                      |
| **Async Support**        | No (synchronous only)                      | Yes (`connect_token_async()`)             |
| **Instance Restriction** | Via config selection                       | Via `TokenValidationSettings`             |
| **Token Validation**     | N/A                                        | Built-in, with security checks            |

## Scripted Usage?

If you're writing scripts for interactive use or running in controlled environments, see
{doc}`client_scripted` for information on config file-based authentication.
