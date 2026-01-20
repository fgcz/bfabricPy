# API Reference: Exceptions and Errors

Complete reference for all exception types in bfabricPy.

```{eval-rst}
.. autoclass:: bfabric.errors.BfabricRequestError
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.errors.BfabricConfigError
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.errors.BfabricInstanceNotConfiguredError
    :members:
    :show-inheritance:
```

## Exception Types

### BfabricRequestError

Raised when the B-Fabric server returns an error in response to a request.

**Attributes:**

- `message` (str): The error message from the server

**When raised:**

- Server rejects a request (authentication, validation, business logic)
- Invalid data or parameters
- Permission denied

**Example:**

```python
from bfabric import Bfabric

client = Bfabric.connect()

try:
    results = client.read(endpoint="sample", obj={"name": "Invalid"})
except RuntimeError as e:
    if hasattr(e, "args") and isinstance(e.args[0], BfabricRequestError):
        error = e.args[0]
        print(f"Server error: {error.message}")
```

### BfabricConfigError

Raised when the bfabricPy configuration is invalid.

**When raised:**

- Configuration file has invalid syntax
- Required fields are missing
- Invalid configuration values
- Cannot find configuration file

**Example:**

```python
from bfabric import Bfabric
from bfabric.errors import BfabricConfigError

try:
    client = Bfabric.connect()
except BfabricConfigError as e:
    print(f"Configuration error: {e}")
```

### BfabricInstanceNotConfiguredError

Raised when a B-Fabric instance is not configured as supported in `TokenValidationSettings`.

**Attributes:**

- `instance_name` (str): The unsupported instance name

**When raised:**

- Using `Bfabric.connect_token()` with a token from an unsupported B-Fabric instance
- Token's `caller` URL is not in the `supported_bfabric_instances` list

**Example:**

```python
from bfabric import Bfabric
from bfabric.errors import BfabricInstanceNotConfiguredError
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=["https://fgcz-bfabric.uzh.ch/bfabric/"],
)

try:
    # Token from unsupported instance
    client, token_data = Bfabric.connect_token(
        token="token_from_test_instance",
        settings=settings,
    )
except BfabricInstanceNotConfiguredError as e:
    print(f"Instance not supported: {e.instance_name}")
```

## See Also

- [Error Handling](../../resources/error_handling.md) - Complete error handling guide
- [Troubleshooting](../../resources/troubleshooting.md) - Solutions to common issues
