# Error Handling

This page covers error types and handling in bfabricPy.

## Exception Types

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

## ResultContainer Error Handling

When using `client.read()`, `client.save()`, or `client.delete()`, operations return a `ResultContainer`:

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Perform a query
results = client.read(endpoint="sample", obj={"name": "MySample"})

# Check if operation was successful
if results.is_success:
    print("Operation successful!")
else:
    print(f"Errors occurred: {results.errors}")
    for error in results.errors:
        print(f"  - {error.message}")
```

### Automatic Error Checking

By default, operations will raise an error if they fail:

```python
# This will raise RuntimeError if the query fails
results = client.read(endpoint="sample", obj={"name": "NonExistent"})

# Access results if successful
for result in results:
    print(result["name"])
```

### Manual Error Checking

You can disable automatic error checking and handle errors manually:

```python
# Disable automatic error checking
results = client.read(endpoint="sample", obj={"name": "MySample"}, check=False)

# Check manually
if results.is_success:
    for result in results:
        print(result["name"])
else:
    print("Query failed:")
    for error in results.errors:
        print(f"  - {error.message}")
```

### Asserting Success

You can use `assert_success()` to raise an error if the operation failed:

```python
results = client.read(endpoint="sample", obj={"name": "MySample"})
results.assert_success()  # Raises RuntimeError if errors occurred
```

## EntityReader Error Handling

The `EntityReader` may raise different types of errors:

### ValueError

Raised when:

- URI is invalid or from unsupported B-Fabric instance
- `bfabric_instance` parameter doesn't match client's configured instance
- All URIs in a batch are not from the same instance or entity type

```python
from bfabric import Bfabric
from bfabric.entities.core.uri import EntityUri

client = Bfabric.connect()
reader = client.reader

try:
    # This will raise ValueError if instance doesn't match
    entity = reader.read_uri(
        uri="https://different-instance.com/bfabric/sample/show.html?id=123"
    )
except ValueError as e:
    print(f"Error: {e}")
```

### TypeError

Raised when:

- `expected_type` parameter is provided but the entity doesn't match

```python
from bfabric import Bfabric
from bfabric.entities import Sample

client = Bfabric.connect()
reader = client.reader

try:
    # This will raise TypeError if entity is not a Sample
    entity = reader.read_id(
        entity_type="project", entity_id=123, expected_type=Sample  # Wrong type!
    )
except TypeError as e:
    print(f"Type error: {e}")
```

### None Returns

For read operations, `None` is returned (not an exception) when:

- Entity is not found in B-Fabric

```python
entity = reader.read_id(entity_type="sample", entity_id=999999)
if entity is None:
    print("Sample not found")
else:
    print(f"Found sample: {entity['name']}")
```

## BfabricRequestError

`BfabricRequestError` represents errors returned by the B-Fabric server:

```python
from bfabric import Bfabric
from bfabric.errors import BfabricRequestError

client = Bfabric.connect()

try:
    results = client.read(endpoint="sample", obj={"name": "Test"})
    results.assert_success()
except RuntimeError as e:
    # Check if it's a BfabricRequestError
    if isinstance(e.args[0], BfabricRequestError):
        error = e.args[0]
        print(f"B-Fabric error: {error.message}")
    else:
        print(f"Other error: {e}")
```

## Configuration Errors

`BfabricConfigError` is raised when configuration is invalid:

```python
from bfabric import Bfabric
from bfabric.errors import BfabricConfigError

try:
    client = Bfabric.connect(config_file_env="INVALID_ENV")
except BfabricConfigError as e:
    print(f"Configuration error: {e}")
```

## Instance Not Configured Error

`BfabricInstanceNotConfiguredError` is raised when using token-based authentication with an unsupported instance:

```python
from bfabric import Bfabric
from bfabric.errors import BfabricInstanceNotConfiguredError
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

client = Bfabric.connect()

try:
    settings = TokenValidationSettings(
        validation_bfabric_instance="https://production.com/bfabric/",
        supported_bfabric_instances=["https://production.com/bfabric/"],
    )

    # This will raise BfabricInstanceNotConfiguredError if token is from different instance
    client2, token_data = Bfabric.connect_token(token=token, settings=settings)
except BfabricInstanceNotConfiguredError as e:
    print(f"Instance not supported: {e}")
```

## Error Handling Patterns

### Pattern 1: Safe Query

```python
def safe_query_sample(client: Bfabric, sample_id: int) -> Entity | None:
    """Query a sample, returning None if not found."""
    try:
        return client.reader.read_id(entity_type="sample", entity_id=sample_id)
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to query sample {sample_id}: {e}")
        return None
```

### Pattern 2: Batch Processing with Error Collection

```python
def process_samples(client: Bfabric, sample_ids: list[int]) -> dict[int, Entity]:
    """Process multiple samples, collecting errors."""
    results = {}
    errors = []

    for sample_id in sample_ids:
        try:
            entity = client.reader.read_id(entity_type="sample", entity_id=sample_id)
            if entity:
                results[sample_id] = entity
            else:
                errors.append(f"Sample {sample_id} not found")
        except ValueError as e:
            errors.append(f"Sample {sample_id}: {e}")

    # Log all errors
    for error in errors:
        logger.warning(error)

    return results
```

### Pattern 3: Write Operations with Retry

```python
import time
from bfabric import Bfabric
from bfabric.errors import BfabricRequestError


def save_with_retry(
    client: Bfabric, endpoint: str, obj: dict, max_retries: int = 3
) -> bool:
    """Save with retry on BfabricRequestError."""
    for attempt in range(max_retries):
        try:
            result = client.save(endpoint=endpoint, obj=obj, check=True)
            return True
        except RuntimeError as e:
            if isinstance(e.args[0], BfabricRequestError):
                logger.warning(f"Attempt {attempt + 1} failed: {e.args[0].message}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
            raise

    return False
```

## Common Error Scenarios

### Authentication Failures

**Symptom**: `BfabricRequestError` with authentication-related message

**Solution**:

- Check credentials in config file
- Verify web service password (not login password)
- Ensure `include_auth=True` when creating client

```python
# Verify credentials
client = Bfabric.connect()
print(f"Connected to: {client.config.base_url}")
print(f"User: {client.auth.login}")
```

### Permission Denied

**Symptom**: `BfabricRequestError` with permission-related message

**Solution**:

- Check user has permission for the operation
- For write operations, ensure user has write permissions
- Use feeder user credentials if needed (see {doc}`client_server`)

### Entity Not Found

**Symptom**: `read_id()` or `read_uri()` returns `None`

**Solution**:

- Verify entity ID and type are correct
- Check that you're connected to the correct B-Fabric instance
- Use `client.exists()` to check existence first

### Invalid URI

**Symptom**: `ValueError` with "Invalid Entity URI" message

**Solution**:

- Verify URI format: `https://<instance>/bfabric/<entity_type>/show.html?id=<id>`
- Use `EntityUri.from_components()` to construct URIs programmatically

```python
from bfabric.entities.core.uri import EntityUri

# Construct URI correctly
uri = EntityUri.from_components(
    bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    entity_type="sample",
    entity_id=123,
)
```

## Best Practices

1. **Always check `is_success`** when using `ResultContainer` with `check=False`
2. **Use specific exception types** rather than catching broad `Exception`
3. **Log errors appropriately** - use `logger.warning()` for recoverable errors, `logger.error()` for fatal errors
4. **Validate before operations** - use `client.exists()` before creating duplicates
5. **Handle `None` returns** from `EntityReader` methods gracefully
6. **Use context managers** for operations that need cleanup
7. **Provide clear error messages** when raising exceptions in your own code
