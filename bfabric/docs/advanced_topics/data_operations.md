# Data Operations

## Upload Datasets

Create a B-Fabric dataset from a CSV (or any Polars DataFrame) by composing the
operations in `bfabric.operations.dataset`:

```python
import polars as pl
from bfabric import Bfabric
from bfabric.operations.dataset import (
    CreateDatasetParams,
    check_for_invalid_characters,
    create_dataset,
)

client = Bfabric.connect()

table = pl.read_csv("data/measurements.csv")
check_for_invalid_characters(table)  # raises on forbidden characters

dataset = create_dataset(
    client=client,
    table=table,
    params=CreateDatasetParams(name="MyMeasurements", container_id=123),
)
print(f"Dataset created with ID: {dataset.id}")
```

`create_dataset` does not validate input — apply `check_for_invalid_characters`
and/or `warn_on_trailing_spaces` from `bfabric.operations.dataset.validation`
beforehand if you need those checks.

## Update Custom Attributes

```{warning}
`update_custom_attributes` is experimental and may change or be removed in future versions.
```

Update custom attributes on any entity by its URI.

```python
from bfabric import Bfabric
from bfabric.entities.core.uri import EntityUri
from bfabric.experimental.update_custom_attributes import update_custom_attributes

client = Bfabric.connect()

custom_attrs = {"status": "processed", "qc_status": "passed"}
uri = EntityUri("https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123")

result = update_custom_attributes(
    client=client,
    entity_uri=uri,
    custom_attributes=custom_attrs,
    replace=False,  # Merge with existing (default)
)

if result.is_success:
    print("Custom attributes updated")
```

### Parameters

- `client`: Bfabric client instance
- `entity_uri`: Entity URI of the entity to update
- `custom_attributes`: Dictionary of custom attribute key-value pairs
- `replace`: If `True`, replace all attributes. If `False` (default), merge with existing

## Use Cases

### Workflow Status Tracking

Track processing status across samples:

```python
# Mark samples as processed
samples = reader.query(entity_type="sample", obj={"projectid": 123})

for uri, sample in samples.items():
    update_custom_attributes(
        client=client,
        entity_uri=uri,
        custom_attributes={"processing_status": "completed"},
    )
```

### QC Result Annotation

Add quality control results:

```python
# Annotate samples with QC results
qc_results = {
    "qc_status": "passed",
    "qc_date": "2025-01-22",
    "qc_score": 0.95,
}

update_custom_attributes(
    client=client,
    entity_uri=sample_uri,
    custom_attributes=qc_results,
)
```

## Limitations

- Custom attributes are B-Fabric specific and may not be available for all entity types
- Attribute names must be valid B-Fabric custom attribute names
- Values are stored as strings in B-Fabric

## See Also

- [Writing Data](../user_guides/writing_data/index.md) - Standard write operations
- [Entity Features](../user_guides/working_with_entities/index.md) - Working with entity objects
- [API Reference: EntityReader](../api_reference/entity_reader/index.md) - EntityReader documentation
