# Experimental: Data Operations

This guide covers experimental features for working with data on B-Fabric entities, including uploading datasets and
updating custom attributes.

```{warning}
Experimental features may change or be removed in future versions. Use at your own risk.
```

## Upload Datasets

The `upload_dataset` feature allows you to create B-Fabric datasets from CSV files.

### Basic Upload

Upload a CSV file as a new dataset:

```python
from pathlib import Path
from bfabric import Bfabric
from bfabric.experimental.upload_dataset import bfabric_save_csv2dataset

client = Bfabric.connect()

csv_file = Path("data/measurements.csv")
result = bfabric_save_csv2dataset(
    client=client,
    csv_file=csv_file,
    dataset_name="MyMeasurements",
    container_id=123,
    workunit_id=None,  # Optional
    sep=",",  # CSV separator
    has_header=True,  # Does CSV have a header row?
    invalid_characters="",  # Characters to reject (e.g., ",")
)

print(f"Dataset created with ID: {result.to_list_dict()[0]['id']}")
```

### Parameters

- **`client`**: Bfabric client instance
- **`csv_file`**: Path to CSV file
- **`dataset_name`**: Name for the new dataset in B-Fabric
- **`container_id`**: ID of the container (e.g., project ID)
- **`workunit_id`**: Optional ID of the workunit to associate with
- **`sep`**: CSV separator (e.g., "," for comma-separated, "\\t" for tab-separated)
- **`has_header`**: Whether the first row contains column names
- **`invalid_characters`**: Characters to reject (e.g., "," to prevent CSV injection)

### Upload to Workunit

Associate dataset with a workunit:

```python
result = bfabric_save_csv2dataset(
    client=client,
    csv_file=csv_file,
    dataset_name="ProcessingResults",
    container_id=123,
    workunit_id=456,  # Associate with workunit
    sep=",",
    has_header=True,
    invalid_characters="",
)
```

### Invalid Character Detection

The function checks for invalid characters in string columns:

```python
# Will raise RuntimeError if any cell contains these characters
result = bfabric_save_csv2dataset(
    client=client,
    csv_file=csv_file,
    dataset_name="MyDataset",
    container_id=123,
    workunit_id=None,
    sep=",",
    has_header=True,
    invalid_characters=",\\n",  # Reject commas and newlines
)
```

### Entity Type Detection

The function automatically detects entity references in column names:

```python
# If CSV has a "project" column with integer IDs,
# it will be treated as a reference to Project entities

# The column type is inferred automatically:
# - Integer columns → "Integer"
# - String columns → "String"
# - Entity references → Appropriate entity type (if all values are valid IDs)
```

## Update Custom Attributes

The `update_custom_attributes` function allows you to update custom attributes on any entity.

### Basic Update

Update custom attributes on an entity:

```python
from bfabric import Bfabric
from bfabric.experimental.update_custom_attributes import update_custom_attributes
from bfabric.entities.core.uri import EntityUri

client = Bfabric.connect()

# Define custom attributes
custom_attrs = {
    "my_field": "value1",
    "another_field": "value2",
}

# Update by URI
uri = "https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123"
result = update_custom_attributes(
    client=client, entity_uri=uri, custom_attributes=custom_attrs
)

if result.is_success:
    print("Custom attributes updated successfully")
```

### Update by Entity Object

Use entity's URI to update:

```python
from bfabric import Bfabric
from bfabric.experimental.update_custom_attributes import update_custom_attributes
from bfabric.entities.cache.context import cache_entities

client = Bfabric.connect()

# Load entity
with cache_entities("sample"):
    sample = client.reader.read_id(entity_type="sample", entity_id=123)

# Update custom attributes
custom_attrs = {
    "status": "processed",
    "qc_status": "passed",
}

result = update_custom_attributes(
    client=client, entity_uri=sample.uri, custom_attributes=custom_attrs
)
```

### Replace vs. Merge

Control whether to replace all custom attributes or merge with existing:

```python
# Replace all existing custom attributes
result = update_custom_attributes(
    client=client,
    entity_uri=uri,
    custom_attributes=new_attrs,
    replace=True,  # Replaces all existing custom attributes
)

# Merge with existing custom attributes
result = update_custom_attributes(
    client=client,
    entity_uri=uri,
    custom_attributes=new_attrs,
    replace=False,  # Adds/updates only specified attributes (default)
)
```

```{warning}
Using `update_custom_attributes` within cache contexts may lead to unexpected behavior if the same entity is
updated by different parts of your application. Be careful when using caching with custom attributes.
```

## Complete Example

```python
from pathlib import Path
from bfabric import Bfabric
from bfabric.experimental.upload_dataset import bfabric_save_csv2dataset
from bfabric.experimental.update_custom_attributes import update_custom_attributes
from bfabric.entities.core.uri import EntityUri

client = Bfabric.connect()

# 1. Upload a CSV as a dataset
csv_file = Path("results.csv")
result = bfabric_save_csv2dataset(
    client=client,
    csv_file=csv_file,
    dataset_name="AnalysisResults",
    container_id=123,
    workunit_id=456,
    sep=",",
    has_header=True,
    invalid_characters="",
)

if not result.is_success:
    print(f"Upload failed: {result.errors}")
    exit(1)

dataset_id = result[0]["id"]
print(f"Created dataset #{dataset_id}")

# 2. Update custom attributes on the dataset
custom_attrs = {
    "processing_date": "2024-01-15",
    "experiment_type": "proteomics",
}

result = update_custom_attributes(
    client=client,
    entity_uri=EntityUri.from_components(
        bfabric_instance=client.config.base_url,
        entity_type="dataset",
        entity_id=dataset_id,
    ),
    custom_attributes=custom_attrs,
)

if result.is_success:
    print("Custom attributes updated successfully")
```

## Error Handling

All experimental functions return a `ResultContainer`:

```python
result = bfabric_save_csv2dataset(...)

if not result.is_success:
    print("Errors occurred:")
    for error in result.errors:
        print(f"  - {error}")
```

## When to Use These Features

### Upload Datasets

- **Good for**: CSV files with structured data that need to be stored as B-Fabric datasets
- **Consider for**: Experimental results, measurement data, batch imports
- **Avoid for**: Large files (use dedicated data stores), non-CSV formats

### Update Custom Attributes

- **Good for**: Adding metadata to entities, tracking processing status, storing derived data
- **Consider for**: Workflow state, QC results, processing parameters
- **Avoid for**: Frequently changing data, large volumes (consider using entity fields instead)

## Next Steps

- {doc}`write_data` - Basic save and delete operations
- {doc}`experimental_workunits` - Workunit definitions and YAML-based workflows
