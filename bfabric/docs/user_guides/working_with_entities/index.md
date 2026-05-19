# Entity Features

Learn about special features and methods provided by specific entity types.

## Overview

bfabricPy provides typed entity classes with type-specific features like Dataset exports, Workunit parameter access, and Resource path methods. These features extend the basic entity API described in [Entity API](../reading_data/entity_api.md).

## Available Entity Types

For complete API documentation, see [API Reference: Entity Types](../../api_reference/entity_types/index.md).

| Entity | Special Features |
| ------- | ---------------- |
| **Dataset** | DataFrame conversion, CSV/Parquet export |
| **Workunit** | Parameter access, output folder calculation |
| **Resource** | Path methods, storage access |
| **Application** | Technology folder name |
| **Executable** | Base64 decoding |
| **Parameter** | Key-value access |
| **User** | Login-based lookup |

## Datasets

Datasets provide rich data access and export capabilities.

```python
from bfabric import Bfabric

client = Bfabric.connect()
dataset = client.reader.read_id(entity_type="dataset", entity_id=12345)
```

### Column Information

```python
# Get column names and types
print(f"Columns: {dataset.column_names}")
print(f"Types: {dataset.column_types}")
```

### DataFrame Conversion

```python
# Convert to Polars DataFrame
df = dataset.to_polars()

# Access column data
for column_name in dataset.column_names:
    column_data = dataset[column_name]
    print(f"{column_name}: {len(column_data)} values")
```

### Export

```python
# Export to CSV or Parquet
dataset.write_csv("output.csv")
dataset.write_parquet("output.parquet")
```

## Workunits

Workunits provide easy access to parameters and output paths.

```python
workunit = client.reader.read_id(entity_type="workunit", entity_id=123)
```

### Parameter Access

Parameters are grouped by context (application, submitter, etc.):

```python
# Application parameters
app_params = workunit.application_parameters
print(f"App params: {len(app_params)}")

# Submitter parameters
submitter_params = workunit.submitter_params
print(f"Submitter params: {len(submitter_params)}")

# All parameters
all_params = workunit.parameters
for param in all_params:
    print(f"  {param.key}: {param.value}")
```

### Output Folder

Calculate the output folder path on storage:

```python
output_folder = workunit.store_output_folder
print(f"Output folder: {output_folder}")
```

## Resources

Resources represent files and provide path calculation methods.

```python
resource = client.reader.read_id(entity_type="resource", entity_id=789)
```

### Path Methods

```python
# Relative path within storage
relative_path = resource.storage_relative_path
print(f"Relative: {relative_path}")

# Absolute path with storage base
absolute_path = resource.storage_absolute_path
print(f"Absolute: {absolute_path}")
```

### Storage Access

Resources have relationships to storage, sample, and workunit:

```python
storage = resource.storage
sample = resource.sample
workunit = resource.workunit
```

## Executables

Executables can decode their content from base64 automatically.

```python
executable = client.reader.read_id(entity_type="executable", entity_id=456)
```

### Decoded Content

```python
# Get decoded string content
if executable.decoded_str:
    print(f"Content: {executable.decoded_str[:100]}...")
```

### Parameter Definitions

```python
# Get parameter definitions
param_defs = executable.parameters
print(f"Defined parameters: {len(param_defs)}")
```

## Users

Users can be looked up by login name.

```python
from bfabric.entities import User

user = User.find_by_login(login="myusername", client=client)
print(f"User ID: {user.id}")
print(f"User name: {user['name']}")
```

## Custom Entity Methods

Some entity types provide custom class methods:

```python
# Find by login (User class)
user = User.find_by_login(login="username", client=client)

# Future entities may provide similar convenience methods
```

## Advanced Usage

### Entity-Specific Relationships

Some entities define specialized relationship accessors:

```python
# Workunit has application relationship
workunit = client.reader.read_id(entity_type="workunit", entity_id=123)
application = workunit.application  # Direct accessor (not via refs)
print(f"Application: {application['name']}")
```

### Combining Features

```python
# Get all datasets from a project and export them
project = client.reader.read_id(entity_type="project", entity_id=456)

for uri, dataset in project.refs.get("member").items():
    dataset_name = dataset["name"]
    dataset.write_csv(f"exports/{dataset_name}.csv")
    print(f"Exported: {dataset_name}")
```

## See Also

- [Entity API](../reading_data/entity_api.md) - Core entity reading and relationships
- [API Reference: Entity Types](../../api_reference/entity_types/index.md) - Complete entity type documentation
- [Reading Data](../reading_data/index.md) - Choosing between ResultContainer and Entity APIs
