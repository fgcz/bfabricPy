# Writing Data

This guide covers basic write operations in bfabricPy: saving, updating, and deleting entities.

## Overview

The `Bfabric` client provides methods for creating, updating, and deleting data in B-Fabric. All write operations
require appropriate permissions.

```{warning}
Write operations modify B-Fabric database. Always ensure you have proper permissions before performing writes
in production environments.
```

## Saving Data

### Save a New Object

Use `client.save()` to create a new object or update an existing one:

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Create a new sample
new_sample = {
    "name": "MySample",
    "projectid": 123,
    "description": "A test sample",
}

result = client.save(endpoint="sample", obj=new_sample)

if result.is_success:
    print(f"Created sample with ID: {result[0]['id']}")
else:
    print(f"Errors: {result.errors}")
```

### Update an Existing Object

To update an existing object, include its ID in the object dictionary:

```python
# Update a sample
updated_sample = {
    "id": 456,
    "name": "Updated Name",
    "description": "Updated description",
}

result = client.save(endpoint="sample", obj=updated_sample)
```

### Save Multiple Objects

You can save multiple objects in a single call:

```python
# Create multiple samples
samples = [
    {"name": "Sample1", "projectid": 123},
    {"name": "Sample2", "projectid": 123},
    {"name": "Sample3", "projectid": 123},
]

result = client.save(endpoint="sample", obj=samples)
```

### Using Different Save Methods

Some endpoints may require a different save method (e.g., "update"):

```python
result = client.save(
    endpoint="sample", obj=obj, method="update"  # Use "update" instead of "save"
)
```

### Error Handling

By default, `client.save()` will raise an error if the operation fails. You can control this behavior:

```python
# Disable automatic error checking
result = client.save(endpoint="sample", obj=obj, check=False)

# Check manually
if not result.is_success:
    print(f"Errors occurred: {result.errors}")
else:
    print("Operation successful")
```

## Deleting Data

### Delete a Single Object

Use `client.delete()` to remove an object by its ID:

```python
# Delete a sample with ID 123
result = client.delete(endpoint="sample", id=123)

if result.is_success:
    print("Sample deleted successfully")
```

### Delete Multiple Objects

You can delete multiple objects in a single call:

```python
# Delete multiple samples
ids_to_delete = [123, 456, 789]
result = client.delete(endpoint="sample", id=ids_to_delete)
```

### Error Handling

Similar to `save()`, you can control error checking:

```python
# Delete with custom error handling
result = client.delete(endpoint="sample", id=123, check=False)

if result.is_success:
    print("Deleted successfully")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

## Checking Existence

Before performing operations, you may want to check if an object exists:

```python
# Check if a sample with a specific name exists
exists = client.exists(endpoint="sample", key="name", value="MySample")

if exists:
    print("Sample exists")
    # Update it
else:
    print("Sample does not exist")
    # Create it
```

You can also check by ID:

```python
# Check if sample with specific ID exists
exists = client.exists(endpoint="sample", key="id", value=123)
```

## Uploading Resources

For small files that should be tracked by B-Fabric (not large experimental data stores):

```python
from pathlib import Path

client = Bfabric.connect()

# Read file content
file_path = Path("/path/to/small_file.txt")
content = file_path.read_bytes()

# Upload to a workunit
result = client.upload_resource(
    resource_name="analysis_results.txt", content=content, workunit_id=123
)

if result.is_success:
    print("Resource uploaded successfully")
```

```{note}
Use `upload_resource()` only for relatively small files that should be tracked by B-Fabric.
For large experimental data, use the dedicated data stores available in your B-Fabric instance.
```

## Complete Example: Create and Update

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Create a new sample
new_sample = {
    "name": "MyNewSample",
    "projectid": 123,
    "description": "Initial description",
}

print("Creating sample...")
result = client.save(endpoint="sample", obj=new_sample)
sample_id = result[0]["id"]
print(f"Created sample #{sample_id}")

# Update the sample
updated_sample = {
    "id": sample_id,
    "description": "Updated description",
}

print("Updating sample...")
result = client.save(endpoint="sample", obj=updated_sample)
print("Sample updated successfully")

# Later, delete the sample
print("Deleting sample...")
result = client.delete(endpoint="sample", id=sample_id)
print("Sample deleted successfully")
```

## Return Values

All write operations return a `ResultContainer`, which provides:

- **`results`**: List of returned objects (updated/created/deleted)
- **`errors`**: List of errors that occurred
- **`is_success`**: Boolean indicating if operation was successful
- **`total_pages_api`**: Number of pages available (for pagination context)

Access the first result:

```python
result = client.save(endpoint="sample", obj=obj)
first_result = result[0]
print(f"ID: {first_result['id']}")
```

## Best Practices

1. **Check permissions first**: Ensure you have write permissions for the endpoint
2. **Use check=False for batch operations**: Handle errors manually for better error reporting
3. **Verify object IDs**: Include `id` when updating existing objects
4. **Check existence**: Use `client.exists()` before creating to avoid duplicates
5. **Handle errors gracefully**: Always check `result.is_success` or handle exceptions

## Next Steps

For more advanced data operations, see:

- {doc}`experimental_data` - Upload datasets from CSV, update custom attributes
- {doc}`experimental_workunits` - Workunit definitions and YAML-based workflows
