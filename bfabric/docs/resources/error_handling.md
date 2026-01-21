# Error Handling

This page covers error types and handling in bfabricPy.

Consult [Exceptions and Errors](../api_reference/exceptions_and_errors/index.md) for a complete API reference for exception types.

## ResultContainer Error Handling

When using `client.read()`, `client.save()`, or `client.delete()`, operations return a `ResultContainer`.

> **Note**: Empty results are not errors. A query that finds no matching records is valid and returns an empty `ResultContainer`. Errors only occur for issues like network failures, authentication problems, or server errors.

### Automatic Error Checking (Default)

By default, operations will raise a `RuntimeError` immediately if they fail:

```python
# This raises RuntimeError if there's a server error
results = client.read(endpoint="sample", obj={"name": "MySample"})

# Access results only if successful
for result in results:
    print(result["name"])

# Empty results are not errors - this is valid and returns an empty list
results = client.read(endpoint="sample", obj={"name": "NonExistentSample"})
```

### Manual Error Checking

To handle errors without exceptions, use `check=False`:

```python
# Disable automatic error checking
results = client.read(endpoint="sample", obj={"name": "MySample"}, check=False)

# Check status manually
if results.is_success:
    for result in results:
        print(result["name"])
else:
    print("Query failed:")
    for error in results.errors:
        print(f"  - {error.message}")
```

Use manual checking when you need to:

- Continue processing even if some operations fail
- Collect errors from multiple operations
- Implement custom error recovery logic

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
