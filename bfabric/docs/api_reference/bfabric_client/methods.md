# Bfabric Client Reference

This page provides a complete reference for the `Bfabric` client class.

## Bfabric Class

The main client class for interacting with B-Fabric:

```{eval-rst}
.. autoclass:: bfabric.Bfabric
    :members: connect, from_config, from_token_data, connect_webapp, connect_token, connect_token_async, read, save, delete, exists, upload_resource, with_auth, config, auth, config_data, reader
    :undoc-members:
    :show-inheritance:
```

## Client Creation Methods

### For Interactive/Scripted Usage

Use `Bfabric.connect()` for scripts and interactive sessions:

```python
from bfabric import Bfabric

# Use default configuration
client = Bfabric.connect()

# Specify environment
client = Bfabric.connect(config_file_env="TEST")

# Use custom config file
client = Bfabric.connect(
    config_file_path="/path/to/config.yml", config_file_env="PRODUCTION"
)

# Without authentication (for tests)
client = Bfabric.connect(config_file_env=None, include_auth=False)
```

See {doc}`client_scripted` for detailed information.

### For Server/Webapp Usage

Use `Bfabric.connect_token()` or `Bfabric.connect_token_async()` for web applications:

```python
from bfabric import Bfabric
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

# Synchronous
settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=["https://fgcz-bfabric.uzh.ch/bfabric/"],
)
client, token_data = Bfabric.connect_token(token=token, settings=settings)

# Asynchronous
client, token_data = await Bfabric.connect_token_async(token=token, settings=settings)
```

See {doc}`client_server` for detailed information.

### From Token Data

If you've already validated a token:

```python
from bfabric import Bfabric
from bfabric.rest.token_data import get_token_data

base_url = "https://fgcz-bfabric.uzh.ch/bfabric/"
token_data = get_token_data(base_url=base_url, token=token)
client = Bfabric.from_token_data(token_data)
```

## Read Operations

### client.read()

Read entities from an endpoint with query criteria:

```python
results = client.read(
    endpoint="sample",
    obj={"name": "MySample", "projectid": 123},
    max_results=100,
    offset=0,
    check=True,
    return_id_only=False,
)
```

**Parameters:**

- `endpoint` (str): The B-Fabric endpoint (e.g., "sample", "project", "workunit")
- `obj` (dict): Query criteria. Multiple values for a field are treated as OR condition, multiple fields as AND condition
- `max_results` (int | None): Maximum results to return. Defaults to 100. `None` for all results
- `offset` (int): Number of results to skip (for pagination)
- `check` (bool): Raise error if query fails. Defaults to `True`
- `return_id_only` (bool): Return only IDs instead of full data

**Returns:** `ResultContainer` with the query results

See {doc}`read_resultcontainer` for more information on working with results.

### client.exists()

Check if an object exists:

```python
exists = client.exists(
    endpoint="sample",
    key="name",
    value="MySample",
    query={"projectid": 123},
    check=True,
)
```

**Parameters:**

- `endpoint` (str): The B-Fabric endpoint to check
- `key` (str): Field name to check
- `value` (int | str): Value to check for
- `query` (dict | None): Additional query conditions (optional)
- `check` (bool): Raise error if query fails. Defaults to `True`

**Returns:** `bool` indicating if object exists

## Write Operations

### client.save()

Create or update objects:

```python
result = client.save(
    endpoint="sample",
    obj={"name": "NewSample", "projectid": 123},
    check=True,
    method="save",
)
```

**Parameters:**

- `endpoint` (str): The B-Fabric endpoint (e.g., "sample", "project")
- `obj` (dict | list\[dict\]): Object(s) to save. Include `id` field for updates
- `check` (bool): Raise error if save fails. Defaults to `True`
- `method` (str): Method to use. Default is `"save"`, but some endpoints require `"update"`

**Returns:** `ResultContainer` with saved/updated objects

**Notes:**

- For new objects, omit the `id` field
- For updates, include the `id` field
- Multiple objects can be saved in a single call by passing a list
- See {doc}`write_data` for more examples

### client.delete()

Delete objects by ID:

```python
result = client.delete(
    endpoint="sample",
    id=123,
    check=True,
)
```

**Parameters:**

- `endpoint` (str): The B-Fabric endpoint
- `id` (int | list\[int\]): Single ID or list of IDs to delete
- `check` (bool): Raise error if delete fails. Defaults to `True`

**Returns:** `ResultContainer` with deleted objects

### client.upload_resource()

Upload a small file as a resource:

```python
from pathlib import Path

client = Bfabric.connect()

file_path = Path("/path/to/file.txt")
content = file_path.read_bytes()

result = client.upload_resource(
    resource_name="myfile.txt",
    content=content,
    workunit_id=456,
    check=True,
)
```

**Parameters:**

- `resource_name` (str): Name for the resource (must be unique per workunit)
- `content` (bytes): File content as bytes
- `workunit_id` (int): Workunit ID to associate with
- `check` (bool): Raise error if upload fails. Defaults to `True`

**Returns:** `ResultContainer` with uploaded resource

**Notes:**

- Only for relatively small files that should be tracked by B-Fabric
- For large experimental data, use dedicated data stores

## Configuration and Authentication

### client.config

Access client configuration:

```python
client = Bfabric.connect()

print(f"Base URL: {client.config.base_url}")
print(f"Engine: {client.config.engine}")
```

### client.auth

Access authentication information:

```python
client = Bfabric.connect()

print(f"Login: {client.auth.login}")
# Password is a SecretStr and not directly accessible
```

**Raises:** `ValueError` if authentication is not available

### client.config_data

Access full configuration data:

```python
client = Bfabric.connect()

print(client.config_data)
```

### client.with_auth()

Context manager to temporarily change authentication:

```python
from bfabric import Bfabric
from bfabric.config import BfabricAuth

client = Bfabric.connect()

# Temporarily use different credentials
with client.with_auth(BfabricAuth(login="other_user", password="other_pass")):
    # All operations in this block use different authentication
    results = client.read(endpoint="sample", obj={"name": "Test"})

# Authentication is restored after the block
```

## EntityReader Access

### client.reader

Access the `EntityReader` for entity-based operations:

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read entities as Entity objects
project = reader.read_id(entity_type="project", entity_id=123)
samples = reader.query(entity_type="sample", obj={"projectid": 123})

# See {doc}`read_entity_api` for more details
```

## Deprecated Methods

### Bfabric.from_config()

**Deprecated:** Use `Bfabric.connect()` instead

```python
# Old way (deprecated)
client = Bfabric.from_config(config_env="PRODUCTION")

# New way
client = Bfabric.connect(config_file_env="PRODUCTION")
```

### Bfabric.connect_webapp()

**Deprecated:** Use `Bfabric.connect_token()` instead

```python
# Old way (deprecated)
client, token_data = Bfabric.connect_webapp(
    token=token, validation_instance_url="https://fgcz-bfabric.uzh.ch/bfabric/"
)

# New way (more secure)
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings

settings = TokenValidationSettings(
    validation_bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    supported_bfabric_instances=["https://fgcz-bfabric.uzh.ch/bfabric/"],
)
client, token_data = Bfabric.connect_token(token=token, settings=settings)
```

## Complete Example

```python
from bfabric import Bfabric
from bfabric.errors import BfabricRequestError

# Create client
client = Bfabric.connect()

print(f"Connected to: {client.config.base_url}")

# Check if sample exists
if not client.exists(endpoint="sample", key="name", value="TestSample"):
    print("Sample doesn't exist, creating it...")

    # Create new sample
    result = client.save(
        endpoint="sample",
        obj={
            "name": "TestSample",
            "projectid": 123,
            "description": "A test sample",
        },
        check=True,
    )

    if result.is_success:
        sample_id = result[0]["id"]
        print(f"Created sample with ID: {sample_id}")
    else:
        print("Failed to create sample:")
        for error in result.errors:
            print(f"  - {error.message}")
else:
    print("Sample already exists")

# Read samples using EntityReader
reader = client.reader
samples = reader.query(entity_type="sample", obj={"projectid": 123})

print(f"Found {len(samples)} samples in project 123")
for uri, sample in samples.items():
    print(f"  - {sample['name']} (ID: {sample.id})")
```

## Related Documentation

- {doc}`client_scripted` - Creating clients for interactive/scripted usage
- {doc}`client_server` - Creating clients for server/webapp usage
- {doc}`write_data` - Detailed guide to write operations
- {doc}`error_handling` - Error handling patterns and exception types
- {doc}`read_resultcontainer` - Working with ResultContainer
- {doc}`read_entity_api` - Working with EntityReader
