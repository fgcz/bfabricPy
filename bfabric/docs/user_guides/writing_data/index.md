# Writing Data

Learn to create, update, and delete entities in B-Fabric.

```{note}
For quick one-off operations, consider using [bfabric-cli API operations](../cli_reference/api_operations.md).
```

## Configuration for Testing

```python
# Customize for your test system
TEST_PROJECT_ID = 3000

# Always connect to test instance
from bfabric import Bfabric

client = Bfabric.connect(config_file_env="TEST")
```

Set up a `TEST` environment in `~/.bfabricpy.yml`. See [Configuration Guide](../../getting_started/configuration.md).

## Example

```python
# Create
new_sample = {
    "name": "TEST_MySample",
    "containerid": TEST_PROJECT_ID,
    "type": "Biological Sample - Generic",
    "description": "A test sample",
}
result = client.save(endpoint="sample", obj=new_sample)
sample_id = result[0]["id"]
print(f"Created: {sample_id}")
```

Inspect the sample in B-Fabric before continuing.

Updates only require the `id` field and the fields whose values should be changed. Be careful with list-valued fields as they will be replaced in their entirety.

```python
# Update
result = client.save(
    endpoint="sample",
    obj={
        "id": sample_id,  # Required for updates
        "description": "Updated description",
    },
)
print("Updated")
```

Inspect the updated sample in B-Fabric. The operation also adds an entry to the `log` tab.

To complete the example and delete the sample:

```python
# Delete
result = client.delete(endpoint="sample", id=sample_id)
print("Deleted")
```

## Error Handling

See [Error Handling](../../resources/error_handling.md) for comprehensive error handling patterns and `ResultContainer` API documentation.
