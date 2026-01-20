# Writing Data

Learn to create, update, and delete entities in B-Fabric.

```{toctree}
:maxdepth: 1
save_update_delete
file_uploads
batch_operations
```

## Overview

bfabricPy provides methods for all write operations through the `Bfabric` client:

| Operation                    | Method                                | Documentation                                                                    |
| ---------------------------- | ------------------------------------- | -------------------------------------------------------------------------------- |
| **Create/Update**            | `client.save(endpoint, obj)`          | [Save, Update, Delete](save_update_delete.md)                                    |
| **Delete**                   | `client.delete(endpoint, id)`         | [Save, Update, Delete](save_update_delete.md)                                    |
| **Upload Files**             | `client.upload_resource()`            | [File Uploads](file_uploads.md)                                                  |
| **Check Existence**          | `client.exists(endpoint, key, value)` | [Save, Update, Delete](save_update_delete.md)                                    |
| **Update Custom Attributes** | `update_custom_attributes()`          | [Experimental Features](../working_with_entities/experimental_features/index.md) |

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

### Example 3: Upload a Small File

```python
from bfabric import Bfabric
from pathlib import Path

client = Bfabric.connect()

# Read file content
file_path = Path("/path/to/small_file.txt")
content = file_path.read_bytes()

# Upload to workunit
result = client.upload_resource(
    resource_name="my_file.txt",
    content=content,
    workunit_id=789,
)

if result.is_success:
    print("File uploaded successfully")
    print(f"Resource ID: {result[0]['id']}")
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

## Next Steps

- [Save, Update, Delete](save_update_delete.md) - Detailed write operation guide
- [File Uploads](file_uploads.md) - Uploading resources
- [Batch Operations](batch_operations.md) - Efficient batch processing
- [Error Handling](../../resources/error_handling.md) - Error types and patterns

## See Also

- [API Reference: Bfabric Client](../../api_reference/bfabric_client/index.md) - Complete client documentation
- [Reading Data](../reading_data/index.md) - Querying B-Fabric
- [Best Practices](../../resources/best_practices.md) - Development guidelines
