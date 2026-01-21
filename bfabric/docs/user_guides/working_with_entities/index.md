# Working with Entities

Learn to work with typed entities, relationships, and entity-specific features.

```{toctree}
:maxdepth: 1
entity_types
dataset_operations
workunit_operations
parameter_access
```

## Overview

bfabricPy provides a rich entity system with typed classes, relationships, and special features for each entity type.

### Why Use Entities?

| Feature | Benefit |
| ------------------- | --------------------------------------------------------------- |
| **Type Safety** | IDE autocomplete, type checking |
| **Relationships** | Navigate connected entities (project → samples → workunits) |
| **Special Methods** | Entity-specific features (Dataset exports, Workunit parameters) |
| **URI Support** | Reference entities across instances |
| **Caching** | Automatic caching for repeated access |

### Entity Types

bfabricPy includes 20+ entity types with different features:

| Entity | Special Features | Documentation |
| --------------- | ------------------------------------------- | --------------------------------------------- |
| **Dataset** | DataFrame conversion, CSV/Parquet export | [Dataset Operations](dataset_operations.md) |
| **Workunit** | Parameter access, output folder calculation | [Workunit Operations](workunit_operations.md) |
| **Sample** | Container relationships | [Entity Types Reference](entity_types.md) |
| **Project** | Sample relationships | [Entity Types Reference](entity_types.md) |
| **Resource** | Path methods, storage access | [Entity Types Reference](entity_types.md) |
| **Application** | Technology information | [Entity Types Reference](entity_types.md) |

For a complete reference of all entity types, see [Entity Types Reference](entity_types.md) or [API Reference: Entity Types](../../api_reference/entity_types/index.md).

## Quick Examples

### Example 1: Access Entity Properties

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read a dataset
dataset = reader.read_id(entity_type="dataset", entity_id=12345)

# Access entity properties
print(f"Dataset ID: {dataset.id}")
print(f"Dataset name: {dataset['name']}")

# Access special features
print(f"Columns: {dataset.column_names}")
print(f"Types: {dataset.column_types}")
```

### Example 2: Navigate Relationships

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Get a workunit
workunit = reader.read_id(entity_type="workunit", entity_id=123)

# Navigate to application (HasOne relationship)
application = workunit.application
print(f"Application: {application['name']}")

# Navigate to parameters (HasMany relationship)
parameters = workunit.parameters
print(f"Number of parameters: {len(parameters)}")

# Access by context
app_params = workunit.application_parameters
print(f"Application params: {app_params}")
```

### Example 3: Use Expected Type for Safety

```python
from bfabric import Bfabric
from bfabric.entities import Dataset

client = Bfabric.connect()
reader = client.reader

# Read with expected type
dataset = reader.read_id(
    entity_type="dataset",
    entity_id=12345,
    expected_type=Dataset,  # Type safety!
)

# IDE knows about Dataset methods
df = dataset.to_polars()
csv = dataset.get_csv()
```

### Example 4: Entity Caching

```python
from bfabric import Bfabric
from bfabric.entities.cache.context import cache_entities

client = Bfabric.connect()
reader = client.reader

# Cache entities for performance
with cache_entities(["sample", "project"], max_size=1000):
    # First access fetches from API
    project1 = reader.read_id(entity_type="project", entity_id=1)

    # Second access uses cache (no API call)
    project2 = reader.read_id(entity_type="project", entity_id=1)

    assert project1 is project2  # Same object
```

## Relationship Patterns

### HasOne (Single Relationship)

```python
# Required relationship
class Workunit(Entity):
    application: HasOne[Application] = HasOne(bfabric_field="application")


# Access
workunit = reader.read_id(entity_type="workunit", entity_id=123)
app = workunit.application
if app is None:
    print("No application")
else:
    print(app["name"])
```

### HasMany (Multiple Relationships)

```python
class Workunit(Entity):
    parameters: HasMany[Parameter] = HasMany(bfabric_field="parameter")


# Access
workunit = reader.read_id(entity_type="workunit", entity_id=123)
params = workunit.parameters

# Get all as list
all_params = params.list
print(f"Parameters: {len(all_params)}")

# Get as DataFrame
params_df = params.polars

# Get just IDs
param_ids = params.ids

# Iterate
for param in params:
    print(f"  {param.key}: {param.value}")
```

### Optional Relationships

```python
class Sample(Entity):
    container: HasOne[Project] = HasOne(bfabric_field="container", optional=True)


# Returns None if no container
sample = reader.read_id(entity_type="sample", entity_id=123)
container = sample.container
if container:
    print(f"Container: {container['name']}")  # Optional check not needed!
```

## Advanced Topics

### EntityReader Methods

- `read_uri()` - Read by URI (string or EntityUri)
- `read_uris()` - Read multiple URIs (efficient batching)
- `read_id()` - Read by type and ID
- `read_ids()` - Read multiple IDs (efficient batching)
- `query()` - Query by search criteria

See [API Reference: EntityReader](../../api_reference/entity_reader/index.md) for complete documentation.

### URI Construction

```python
from bfabric.entities.core.uri import EntityUri

# Parse URI
uri = EntityUri("https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123")
print(uri.components.entity_type)  # "sample"
print(uri.components.entity_id)  # 123

# Construct URI
uri = EntityUri.from_components(
    bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    entity_type="sample",
    entity_id=123,
)
print(uri)  # Full URI string
```

## Next Steps

- [Entity Types Reference](entity_types.md) - Complete entity type documentation
- [Dataset Operations](dataset_operations.md) - Working with datasets
- [Workunit Operations](workunit_operations.md) - Working with workunits
- [Entity Relationships](entity_relationships.md) - Deep dive into relationships
- [Caching for Performance](caching_for_performance.md) - Performance optimization

## See Also

- [API Reference: Entity Types](../../api_reference/entity_types/index.md) - Auto-generated entity documentation
- [API Reference: EntityReader](../../api_reference/entity_reader/index.md) - Complete EntityReader documentation
- [Reading Data](../reading_data/index.md) - Query strategies
