# Creating a Client

bfabricPy supports different authentication methods depending on your use case.

```{toctree}
:maxdepth: 1
interactive_scripted_usage
server_webapp_usage
```

## Choose Your Approach

| Use Case                                   | Method                               | Documentation                                                 |
| ------------------------------------------ | ------------------------------------ | ------------------------------------------------------------- |
| Scripts, local tools, interactive sessions | `Bfabric.connect()` with config file | [Interactive/Scripted Usage](interactive_scripted_usage.md)   |
| Web servers, web apps, token-based auth    | `Bfabric.connect_token()` with token | [Server/Webapp Usage](server_webapp_usage.md)                 |
| Containerized deployments, CI/CD           | Environment variables                | [Configuration Guide](../../getting_started/configuration.md) |

## Quick Start

### For Scripts (Most Common)

```python
from bfabric import Bfabric

# Uses ~/.bfabricpy.yml
client = Bfabric.connect()

# Verify connection
print(f"Connected to: {client.config.base_url}")
```

### For Web Apps

```python
from bfabric import Bfabric
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

# Validate token from B-Fabric webapp
settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=["https://fgcz-bfabric.uzh.ch/bfabric/"],
)

client, token_data = Bfabric.connect_token(token=token, settings=settings)
print(f"Authenticated as: {token_data.user}")
```

## Client Features

Once you have a client, you can:

- **Read data**: `client.read(endpoint, obj)`
- **Save entities**: `client.save(endpoint, obj)`
- **Delete entities**: `client.delete(endpoint, id)`
- **Check existence**: `client.exists(endpoint, key, value)`
- **Upload files**: `client.upload_resource(...)`
- **Access EntityReader**: `client.reader.read_id(...)`

See [Bfabric Client Reference](../../api_reference/bfabric_client/index.md) for complete method documentation.

## Configuration Options

### Without Authentication (Tests)

```python
# For tests or read-only operations
client = Bfabric.connect(
    config_file_env=None,
    include_auth=False,
)
```

### Custom Config File

```python
from pathlib import Path

client = Bfabric.connect(
    config_file_path=Path("/custom/config.yml"),
    config_file_env="TEST",
)
```

### Switching Credentials

```python
from bfabric.config import BfabricAuth

client = Bfabric.connect()

# Temporarily use different credentials
with client.with_auth(BfabricAuth(login="other_user", password="other_pass")):
    # Operations in this block use different auth
    results = client.read(endpoint="sample", obj={"name": "Test"})

# Original credentials restored
```

## See Also

- [Configuration Guide](../../getting_started/configuration.md) - Setting up config files
- [API Reference: Bfabric Client](../../api_reference/bfabric_client/index.md) - Complete client documentation
- [Error Handling](../../resources/error_handling.md) - Authentication errors
