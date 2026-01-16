# Entity API

The Entity API provides object-oriented access to B-Fabric data with lazy-loading relationships and automatic caching. This is ideal for
working with entities, navigating relationships, and using URIs to reference data.

## Overview

Access the Entity API through `client.reader`, which returns an `EntityReader` instance:

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader  # EntityReader instance
```

## Reading Entities

### By URI

Read entities by their B-Fabric URIs:

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
entities = reader.read_uris(uris)  # Returns dict[URI, Entity]
```

### By ID

Read entities by type and ID:

```python
# Single entity
sample = reader.read_id(entity_type="sample", entity_id=123)

# Multiple entities of the same type
entities = reader.read_ids(entity_type="sample", entity_ids=[123, 456, 789])
```

### By Query

Query entities with search criteria:

```python
# Find samples by name
entities = reader.query(entity_type="sample", obj={"name": "MySample"}, max_results=100)

# Find projects with specific criteria
entities = reader.query(entity_type="project", obj={"name": "Test", "status": "Active"})
```

## Entity Objects

When you read entities through the Entity API, you get `Entity` objects with typed properties:

### Basic Properties

```python
sample = reader.read_id(entity_type="sample", entity_id=123)

# Entity identifier
print(sample.id)  # 123
print(sample.classname)  # "sample"
print(sample.bfabric_instance)  # "https://fgcz-bfabric.uzh.ch/bfabric/"

# Entity URI
uri = sample.uri
print(uri)  # EntityUri object

# Raw data dictionary
data = sample.data_dict
```

### Accessing Data

Entities support dictionary-like access to their data:

```python
# Check if a field exists
if "name" in sample:
    name = sample["name"]

# Get a field with default
name = sample.get("name", "Unknown")

# Direct attribute access (for top-level fields)
name = sample["name"]
```

### Custom Attributes

If an entity has custom attributes:

```python
try:
    attrs = sample.custom_attributes
    print(attrs["my_custom_field"])
except AttributeError:
    print("No custom attributes")
```

## Relationships and References

Entities can have relationships to other entities. These are accessed via the `refs` property:

```python
sample = reader.read_id(entity_type="sample", entity_id=123)

# Access a related project (one-to-one)
project = sample.refs.get("container")

# Access related workunits (one-to-many)
workunits = sample.refs.get("member")
```

### Lazy Loading

Relationships are lazy-loaded, meaning they're only fetched from B-Fabric when you first access them:

```python
sample = reader.read_id(entity_type="sample", entity_id=123)
# At this point, project is not loaded

project = sample.refs.get("container")
# Now project is loaded from B-Fabric

# Accessing again uses cached result
project = sample.refs.get("container")
# No additional API call
```

### Checking if Loaded

Check if a reference is already loaded:

```python
if sample.refs.is_loaded("container"):
    print("Project already loaded")
else:
    print("Project will be loaded on first access")
```

### Available References

Get all available reference URIs without loading the entities:

```python
all_refs = sample.refs.uris
print(all_refs)
# {"container": ".../project/show.html?id=456", "member": [...]}
```

## EntityReader Caching

The EntityReader automatically caches entities to minimize API calls:

```python
reader = client.reader

# First call fetches from API
sample1 = reader.read_id(entity_type="sample", entity_id=123)

# Second call uses cache (no API call)
sample2 = reader.read_id(entity_type="sample", entity_id=123)

# Both are the same object
assert sample1 is sample2
```

### Cache Benefits

- **Reduced API calls**: Repeated entity accesses use cached data
- **Consistent objects**: Same entity reference returns the same object
- **Performance**: Especially beneficial when navigating relationships

### Reading Multiple Entities

When reading multiple entities, the API is optimized:

```python
# Efficient single API call
entities = reader.read_ids(entity_type="sample", entity_ids=[123, 456, 789])

# Returns dict mapping URI to entity
for uri, entity in entities.items():
    print(f"{uri}: {entity['name']}")
```

## Entity URIs

URIs uniquely identify entities across B-Fabric instances:

```python
# Parse a URI
from bfabric.entities.core.uri import EntityUri

uri = EntityUri("https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123")
print(uri.components.entity_type)  # "sample"
print(uri.components.entity_id)  # 123
print(uri.components.bfabric_instance)  # "https://fgcz-bfabric.uzh.ch/bfabric/"

# Construct a URI
uri = EntityUri.from_components(
    bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    entity_type="sample",
    entity_id=123,
)
```

## Custom Entity Classes

bfabricPy provides custom entity classes for common types (e.g., `Project`, `Sample`, `Workunit`). These can provide
type-specific methods and properties:

```python
from bfabric import Project, Sample

# Read as specific entity type
project = reader.read_id(entity_type="project", entity_id=123, expected_type=Project)
# Returns a Project instance instead of generic Entity
```

Custom entity classes inherit from `Entity` and add type-specific functionality.

## Example: Working with Relationships

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Get a project
project = reader.read_id(entity_type="project", entity_id=123)

# Access related samples
samples = project.refs.get("member")

# For each sample, access its workunits
for sample in samples:
    workunits = sample.refs.get("member")
    print(f"Sample {sample.id}: {len(workunits)} workunits")
```

## Example: Entity Navigation

```python
# Load multiple entities efficiently
uris = [
    "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=123",
    "https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=456",
]

entities = reader.read_uris(uris)

for uri, entity in entities.items():
    if entity:
        print(f"Loaded {entity.classname} #{entity.id}")
        print(f"  URI: {uri}")
    else:
        print(f"Not found: {uri}")
```

## Comparison to ResultContainer API

If you find yourself needing any of the following, consider using {doc}`read_resultcontainer` instead:

- Working with raw dictionary data
- Exporting directly to DataFrames without entity overhead
- Simple queries without relationships
- Full control over data structure
