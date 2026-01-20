# API Reference: EntityReader

Complete reference for the `EntityReader` class.

```{eval-rst}
.. autoclass:: bfabric.entities.core.entity_reader.EntityReader
    :members:
    :undoc-members:
    :show-inheritance:
```

## Overview

The `EntityReader` provides methods to read B-Fabric entities as typed objects with caching support.

### Key Features

- **URI Support**: Read entities by their B-Fabric URIs
- **Batch Operations**: Efficiently read multiple entities
- **Caching**: Automatic caching with `cache_entities()` context
- **Type Safety**: Use `expected_type` parameter for type checking
- **Query Support**: Search entities by criteria

## Quick Examples

### Read by URI

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Single entity
uri = "https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123"
sample = reader.read_uri(uri)

# Multiple entities (mixed types)
uris = [
    "https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123",
    "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=456",
]
entities = reader.read_uris(uris)
```

### Read by ID

```python
# Single entity
sample = reader.read_id(entity_type="sample", entity_id=123)

# Multiple entities of same type
samples = reader.read_ids(entity_type="sample", entity_ids=[123, 456, 789])
```

### Query

```python
# Search by criteria
samples = reader.query(
    entity_type="sample",
    obj={"name": "MySample", "projectid": 123},
    max_results=100,
)
```

### With Type Safety

```python
from bfabric.entities import Sample

# Read with expected type
sample = reader.read_id(
    entity_type="sample",
    entity_id=123,
    expected_type=Sample,  # Type-safe!
)

# IDE knows about Sample methods
print(sample.container)  # Autocomplete available
```

### With Caching

```python
from bfabric.entities.cache.context import cache_entities

# Cache entities for performance
with cache_entities(["sample", "project"], max_size=1000):
    # First access fetches from API
    project1 = reader.read_id(entity_type="project", entity_id=1)

    # Second access uses cache (no API call)
    project2 = reader.read_id(entity_type="project", entity_id=1)

    assert project1 is project2  # Same object
```

## See Also

- [Reading Data](../../user_guides/reading_data/entity_api.md) - Guide to using EntityReader
- [Entity Types](../entity_types/index.md) - Reference for all entity types
- [Caching for Performance](../../user_guides/reading_data/caching_for_performance.md) - Performance optimization
