# Reading Data

Learn to query B-Fabric and retrieve data using different approaches.

```{toctree}
:maxdepth: 1
resultcontainer_api
entity_api
entity_relationships
caching_for_performance
dataset_operations
```

## Choose Your Approach

bfabricPy provides two complementary APIs for reading data:

| Approach                | Primary Class             | Best For                                        | Documentation                                 |
| ----------------------- | ------------------------- | ----------------------------------------------- | --------------------------------------------- |
| **ResultContainer API** | `ResultContainer`         | Simple queries, data analysis, DataFrame export | [ResultContainer API](resultcontainer_api.md) |
| **Entity API**          | `Entity` / `EntityReader` | Typed entities, relationships, URI access       | [Entity API](entity_api.md)                   |

## Quick Comparison

| Feature           | ResultContainer API           | Entity API                           |
| ----------------- | ----------------------------- | ------------------------------------ |
| **Entry Point**   | `client.read(endpoint, obj)`  | `client.reader`                      |
| **Return Type**   | Dictionaries (raw data)       | Entity objects (typed)               |
| **Relationships** | Manual handling               | Lazy-loading via `entity.refs`       |
| **Caching**       | Manual                        | Automatic (via `cache_entities()`)   |
| **URI Support**   | Limited                       | Full URI-based access                |
| **Data Export**   | Polars DataFrames             | Via `data_dict`                      |
| **Use Case**      | Simple queries, data analysis | Working with entities, relationships |

## Examples

### Example 1: Simple Query (ResultContainer)

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Simple query with ResultContainer API
samples = client.read(
    endpoint="sample",
    obj={"projectid": 123},
    max_results=100,
)

print(f"Found {len(samples)} samples")
for sample in samples:
    print(f"  - {sample['name']} (ID: {sample['id']})")
```

### Example 2: Typed Entities (Entity API)

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Query with Entity API
samples = reader.query(
    entity_type="sample",
    obj={"projectid": 123},
)

print(f"Found {len(samples)} samples")
for uri, sample in samples.items():
    print(f"  - {sample['name']} (ID: {sample.id})")
```

### Example 3: Relationship Navigation

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Get a project and navigate to its samples
project = reader.read_id(entity_type="project", entity_id=123)

# Access related samples (lazy-loaded)
samples = project.refs.get("member")
print(f"Project has {len(samples)} samples")

for sample in samples:
    # Access sample's workunits
    workunits = sample.refs.get("member")
    print(f"  Sample {sample.id}: {len(workunits)} workunits")
```

## Next Steps

- [ResultContainer API](resultcontainer_api.md) - Raw data queries and DataFrame export
- [Entity API](entity_api.md) - Typed entities and relationships
- [Entity Relationships](entity_relationships.md) - Working with entity references
- [Caching for Performance](caching_for_performance.md) - Optimize repeated queries
- [Dataset Operations](dataset_operations.md) - Working with datasets

## See Also

- [Working with Entities](../working_with_entities/index.md) - Entity type reference
- [API Reference: EntityReader](../../api_reference/entity_reader/index.md) - Complete EntityReader documentation
- [Error Handling](../../resources/error_handling.md) - Query error handling
