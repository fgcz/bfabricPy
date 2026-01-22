# Writing Data

Learn to create, update, and delete entities in B-Fabric.

```{note}
For quick one-off operations, consider using [bfabric-cli API operations](../cli_reference/api_operations.md).
```

## Understanding the Write API

bfabricPy's write operations are **thin wrappers** around B-Fabric's SOAP webservices. This means:

- **No local validation**: bfabricPy passes your data directly to B-Fabric
- **Field requirements**: You need to know what fields B-Fabric expects for each entity type
- **Error handling**: Validation errors come from B-Fabric, not bfabricPy
- **Direct passthrough**: The API forwards requests with minimal processing

To write to B-Fabric effectively, you'll need some familiarity with:

- B-Fabric entity types and their field structures
- Which fields are required vs optional
- Relationship fields (e.g., `containerid`, `applicationid`)

Use the CLI to discover field requirements:

```bash
# Inspect endpoint structure
bfabric-cli api inspect sample

# Inspect specific method
bfabric-cli api inspect sample save

# Read existing records to see field examples
bfabric-cli api read sample --limit 1 --format json
```

## Configuration for Testing

Set up a `TEST` environment in `~/.bfabricpy.yml`, if you don't already have one.
See [Configuration Guide](../../getting_started/configuration.md) for details.

```python
# Customize for your test system
TEST_PROJECT_ID = 3000

# Always connect to test instance
from bfabric import Bfabric

client = Bfabric.connect(config_file_env="TEST")
```

## Core Operations

### Create

Create new entities using `client.save()` without an `id` field:

```python
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

**Tips:**

- Include all required fields for the entity type
- Omit the `id` field - B-Fabric will assign one
- The `ResultContainer` returns the created object with its new ID

### Update

Updates require the `id` field and only the fields you want to change:

```python
result = client.save(
    endpoint="sample",
    obj={
        "id": sample_id,  # Required for updates
        "description": "Updated description",
    },
)
print("Updated")
```

**Important warnings:**

- **List fields**: List-valued fields (e.g., tags, custom attributes) will be **replaced entirely**, not merged
- **Relationships**: Be careful when modifying relationship fields like `containerid` or `applicationid`
- **Log entries**: Updates create log entries visible in B-Fabric's "log" tab

### Delete

Delete entities by ID:

```python
result = client.delete(endpoint="sample", id=sample_id)
print("Deleted")
```

**Warning:** Deletion is permanent. Consider using TEST environment first.

## Advanced Operations

### Batch Operations

Save multiple objects in a single API call for efficiency:

```python
# Create multiple samples
objects = [
    {
        "name": "Sample1",
        "containerid": TEST_PROJECT_ID,
        "type": "Biological Sample - Generic",
    },
    {
        "name": "Sample2",
        "containerid": TEST_PROJECT_ID,
        "type": "Biological Sample - Generic",
    },
    {
        "name": "Sample3",
        "containerid": TEST_PROJECT_ID,
        "type": "Biological Sample - Generic",
    },
]
result = client.save(endpoint="sample", obj=objects)

# Process all results
for saved_object in result:
    print(f"Created: {saved_object['id']} - {saved_object['name']}")
```

### The `method` Parameter

Most endpoints use `method="save"` (the default), but some require specific methods:

```python
# Default method (works for most endpoints)
result = client.save(endpoint="sample", obj={"name": "Test"})

# Explicit method
result = client.save(endpoint="sample", obj={"name": "Test"}, method="save")

# Some endpoints may require different methods
result = client.save(endpoint="special_endpoint", obj=data, method="update")
```

Check the B-Fabric documentation or use `bfabric-cli api inspect` to determine if a specific method is required.

### Checking for Existence

Avoid creating duplicates by checking existence first:

```python
# Check if sample exists with given name
if not client.exists(endpoint="sample", key="name", value="TEST_MySample"):
    # Only create if doesn't exist
    result = client.save(
        endpoint="sample",
        obj={"name": "TEST_MySample", "containerid": TEST_PROJECT_ID},
    )
    sample_id = result[0]["id"]
    print(f"Created new sample: {sample_id}")
else:
    print("Sample already exists, skipping creation")
```

Use additional query conditions for more specific checks:

```python
# Check for sample with specific name in specific project
if not client.exists(
    endpoint="sample",
    key="name",
    value="TEST_MySample",
    query={"containerid": TEST_PROJECT_ID},
):
    # Safe to create
    pass
```

### Deleting Multiple Entities

Delete multiple entities in a single call:

```python
# Delete by list of IDs
result = client.delete(endpoint="sample", id=[1001, 1002, 1003])
print(f"Deleted {len(result)} samples")
```

## Common Writable Endpoints

| Endpoint | Description | Common Fields |
| -------- | ----------- | ------------- |
| `sample` | Biological samples | `name`, `containerid`, `type`, `description` |
| `project` | Projects | `name`, `description` |
| `order` | Orders | `name`, `description` |
| `container` | Projects and orders | `name`, `description` |
| `workunit` | Workunits | `name`, `applicationid`, `containerid`, `status` |
| `resource` | Resources | `name`, `workunitid`, `base64` (content), `relativepath` |
| `importresource` | Import resources | `name`, `containerid`, `relativepath`, `filechecksum`, `size` |
| `workflow` | Workflows | `containerid`, `workflowtemplateid` |
| `workflowstep` | Workflow steps | `workflowid`, `workflowtemplatestepid`, `workunitid` |

Use `bfabric-cli api inspect <endpoint>` to see complete field lists.

## Response Handling

### Successful Operations

```python
result = client.save(endpoint="sample", obj={"name": "Test", "containerid": 123})

# ResultContainer with saved objects
for saved_object in result:
    print(f"ID: {saved_object['id']}")
    print(f"Name: {saved_object['name']}")
    print(f"Created: {saved_object['created']}")

# Access as list
objects = result.to_list_dict()
```

### Handling Errors

```python
# Manual error handling
result = client.save(endpoint="sample", obj={"name": "Test"}, check=False)

if result.is_success:
    print("Saved successfully")
    print(f"ID: {result[0]['id']}")
else:
    print("Save failed:")
    for error in result.errors:
        print(f"  - {error.message}")
```

See [Error Handling](../error_handling.md) for comprehensive error handling patterns.

## Real-World Patterns

### Pattern 1: Safe Create-or-Update

```python
def create_or_update_sample(client, name, containerid, **attrs):
    """Create sample if it doesn't exist, otherwise update it."""
    # Try to find existing sample
    result = client.read(
        endpoint="sample",
        obj={"name": name, "containerid": containerid},
        max_results=1,
    )

    if len(result) > 0:
        # Update existing
        obj = {"id": result[0]["id"], **attrs}
        return client.save(endpoint="sample", obj=obj)
    else:
        # Create new
        obj = {"name": name, "containerid": containerid, **attrs}
        return client.save(endpoint="sample", obj=obj)
```

### Pattern 2: Creating Related Objects

```python
# Create a workunit with parameters
workunit = client.save(
    endpoint="workunit",
    obj={
        "name": "My Analysis",
        "applicationid": 123,
        "containerid": 456,
        "status": "WAITING",
    },
)
workunit_id = workunit[0]["id"]

# Add parameters to the workunit
client.save(
    endpoint="parameter",
    obj={
        "workunitid": workunit_id,
        "key": "param1",
        "value": "value1",
    },
)
```

## Error Handling

See [Error Handling](../error_handling.md) for comprehensive error handling patterns and `ResultContainer` API documentation.
