# API Reference: Token Data

Complete reference for the `TokenData` class.

```{eval-rst}
.. autoclass:: bfabric.rest.token_data.TokenData
    :members:
    :undoc-members:
    :show-inheritance:
```

## Overview

`TokenData` represents token information received from B-Fabric webapp authentication.

## Properties

| Property           | Type     | Description                              |
| ------------------ | -------- | ---------------------------------------- |
| `user`             | str      | B-Fabric user login                      |
| `user_ws_password` | str      | Web service password for the user        |
| `application_id`   | int      | Application ID                           |
| `entity_class`     | str      | Entity class name                        |
| `entity_id`        | int      | Entity ID                                |
| `job_id`           | int      | External job ID                          |
| `caller`           | str      | B-Fabric instance URL                    |
| `token_expires`    | datetime | Token expiration time                    |
| `web_service_user` | bool     | Whether user has web service permissions |

## Quick Examples

### Basic Token Access

```python
from bfabric import Bfabric
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=["https://fgcz-bfabric.uzh.ch/bfabric/"],
)

client, token_data = Bfabric.connect_token(token=token, settings=settings)

print(f"Authenticated as: {token_data.user}")
print(f"Application ID: {token_data.application_id}")
print(f"Entity: {token_data.entity_class}#{token_data.entity_id}")
```

### Check Token Expiration

```python
from datetime import datetime, timezone, timedelta

client, token_data = Bfabric.connect_token(token=token, settings=settings)

# Check if token expires soon
time_until_expiry = token_data.token_expires - datetime.now(timezone.utc)
if time_until_expiry < timedelta(hours=1):
    print("Warning: Token expires in less than 1 hour!")
```

### Check Web Service Permissions

```python
client, token_data = Bfabric.connect_token(token=token, settings=settings)

if not token_data.web_service_user:
    raise PermissionError("User does not have web service permissions")
```

### Load Associated Entity

```python
client, token_data = Bfabric.connect_token(token=token, settings=settings)

# Load entity from token data
entity = token_data.load_entity(client=client)

print(f"Loaded entity: {entity}")
```

## See Also

- [Token Authentication](../../advanced_topics/token_authentication/index.md) - Deep dive into token-based auth
- [Server/Webapp Usage](../../user_guides/creating_a_client/server_webapp_usage.md) - Server authentication guide
