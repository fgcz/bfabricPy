# Writing Data

Learn to create, update, and delete entities in B-Fabric.

```{note}
For quick one-off operations or shell scripts, consider using the [bfabric-cli API operations](../cli_reference/api_operations.md) instead of Python scripts.
```

## Overview

bfabricPy provides methods for all write operations through the `Bfabric` client:

| Operation                    | Method                                |
| ---------------------------- | ------------------------------------- |
| **Create/Update**            | `client.save(endpoint, obj)`          |
| **Delete**                   | `client.delete(endpoint, id)`         |
| **Check Existence**          | `client.exists(endpoint, key, value)` |
| **Update Custom Attributes** | `update_custom_attributes()`          |

```{note}
`client.upload_resource()` is available for small files (configurations, scripts, metadata). Use dedicated data stores for large experimental data.
```

## Quick Start

### Creating a New Sample

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Create a new sample
new_sample = {
    "name": "MyNewSample",
    "projectid": 123,
    "description": "A test sample",
}

result = client.save(endpoint="sample", obj=new_sample)

if result.is_success:
    sample_id = result[0]["id"]
    print(f"Created sample with ID: {sample_id}")
else:
    print(f"Errors: {result.errors}")
```

### Updating an Existing Sample

```python
# Update a sample
updated_sample = {
    "id": 456,  # Include ID for updates
    "name": "Updated Name",
    "description": "Updated description",
}

result = client.save(endpoint="sample", obj=updated_sample)
print("Sample updated successfully")
```

### Deleting a Sample

```python
# Delete a sample
result = client.delete(endpoint="sample", id=456)

if result.is_success:
    print("Sample deleted successfully")
else:
    print(f"Errors: {result.errors}")
```

## Examples

### Example 1: Create or Update Pattern

```python
from bfabric import Bfabric

client = Bfabric.connect()

sample_name = "MySample"
project_id = 123

# Check if sample exists
if client.exists(endpoint="sample", key="name", value=sample_name):
    print(f"Sample {sample_name} exists, updating...")
    # Update existing sample
    # First, query to get the ID
    existing = client.read(
        endpoint="sample",
        obj={"name": sample_name},
        max_results=1,
    )
    sample_id = existing[0]["id"]

    result = client.save(
        endpoint="sample",
        obj={
            "id": sample_id,
            "description": "Updated description",
        },
    )
else:
    print(f"Sample {sample_name} does not exist, creating...")
    # Create new sample
    result = client.save(
        endpoint="sample",
        obj={
            "name": sample_name,
            "projectid": project_id,
            "description": "Initial description",
        },
    )
```

### Example 2: Batch Create

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Create multiple samples in one call
samples = [{"name": f"Sample{i}", "projectid": 123} for i in range(1, 4)]

result = client.save(endpoint="sample", obj=samples)

if result.is_success:
    print(f"Created {len(result)} samples")
    for sample in result:
        print(f"  - {sample['name']} (ID: {sample['id']})")
```

## Best Practices

### 1. Check Existence Before Creating

Avoid duplicate entities by checking existence first:

```python
if client.exists(endpoint="sample", key="name", value="MySample"):
    print("Sample already exists")
    # Handle appropriately
else:
    # Create new sample
    client.save(endpoint="sample", obj={"name": "MySample", "containerid": 3000})
```

### 2. Use check=False for Batch Operations

Handle errors manually for better error reporting:

```python
results = client.save(
    endpoint="sample",
    obj=batch_of_samples,
    check=False,  # Don't raise on errors
)

if results.is_success:
    print("All samples created successfully")
else:
    print("Some errors occurred:")
    for error in results.errors:
        print(f"  - {error.message}")
```

### 3. Update Workunit State Correctly

When updating workunits with many resources, follow the processing state pattern:

```python
# 1. Set to processing
client.save(endpoint="workunit", obj={"id": wu_id, "status": "processing"})

# 2. Make all updates
client.save(endpoint="resource", obj=resources_list)
client.save(endpoint="workunit", obj={"id": wu_id, "description": "..."})

# 3. Set to available
client.save(endpoint="workunit", obj={"id": wu_id, "status": "available"})
```

See [Good to Know: Updating Workunits](../../resources/good_to_know.md) for details.

### 4. Verify IDs for Updates

Always include the `id` field when updating existing entities:

```python
# Update (correct)
updated = {"id": 123, "name": "New Name"}

# Create (incorrect - creates new entity)
new_entity = {"name": "New Name"}
```

### 5. Handle Permissions

Not all users have write permissions. Check before attempting writes:

```python
# Test write permissions
test_result = client.read(
    endpoint="sample",
    obj={"id": 999999},
    max_results=1,
)

if not test_result.is_success:
    print("Insufficient permissions for write operations")
```

### 6. Use Alternative Save Methods When Needed

Most endpoints use the default "save" method, but some may require "update":

```python
# Use alternative method when required
result = client.save(
    endpoint="sample", obj=obj, method="update"  # Some endpoints require this
)
```

## Error Handling

### ResultContainer Error Checking

```python
result = client.save(endpoint="sample", obj=new_sample)

if result.is_success:
    print("Success")
else:
    print("Errors occurred:")
    for error in result.errors:
        print(f"  - {error.message}")
```

### Manual Error Checking

```python
result = client.save(endpoint="sample", obj=new_sample, check=False)

# Handle errors manually
if result.errors:
    for error in result.errors:
        print(f"Error: {error.message}")
        # Custom error handling
else:
    print("Success")
```

## See Also

- [API Reference: Bfabric Client](../../api_reference/bfabric_client/index.md) - Complete client documentation
- [Reading Data](../reading_data/index.md) - Querying B-Fabric
- [bfabric-cli API Operations](../cli_reference/api_operations.md) - Command-line interface for CRUD operations
- [Best Practices](../../resources/best_practices.md) - Development guidelines
