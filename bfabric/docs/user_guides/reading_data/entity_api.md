# Entity API

The Entity API provides object-oriented access to B-Fabric data with lazy-loading relationships and automatic caching. Access it through `client.reader`, which returns an `EntityReader` instance.

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

```{eval-rst}
.. automethod:: bfabric.entities.core.entity_reader.EntityReader.read_uri
    :noindex:
.. automethod:: bfabric.entities.core.entity_reader.EntityReader.read_uris
    :noindex:
```

### By ID

Read entities by type and ID:

```python
# Single entity
sample = reader.read_id(entity_type="sample", entity_id=123)

# Multiple entities of the same type
entities = reader.read_ids(entity_type="sample", entity_ids=[123, 456, 789])
```

```{eval-rst}
.. automethod:: bfabric.entities.core.entity_reader.EntityReader.read_id
    :noindex:
.. automethod:: bfabric.entities.core.entity_reader.EntityReader.read_ids
    :noindex:
```

### By Query

Query entities with search criteria:

```python
# Find samples by name
entities = reader.query(entity_type="sample", obj={"name": "MySample"}, max_results=100)
```

```{eval-rst}
.. automethod:: bfabric.entities.core.entity_reader.EntityReader.query
    :noindex:
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
```

## Relationships and References

Entities can have relationships to other entities, accessed via the `refs` property. These are **lazy-loaded**, meaning they're only fetched from B-Fabric when you first access them.

```python
sample = reader.read_id(entity_type="sample", entity_id=123)

# Access a related project (one-to-one)
project = sample.refs.get("container")

# Access related workunits (one-to-many)
workunits = sample.refs.get("member")
```

Check if a reference is already loaded:

```python
if sample.refs.is_loaded("container"):
    print("Project already loaded")
```

## Custom Entity Classes

bfabricPy provides custom entity classes for common types (e.g., `Project`, `Sample`, `Workunit`) which provide type-specific methods and properties:

```python
from bfabric import Project

# Read as specific entity type
project = reader.read_id(entity_type="project", entity_id=123, expected_type=Project)
```

## Current Limitations

1. **Single B-Fabric Instance**: Query operations only work with the client's configured B-Fabric instance.
2. **URI Validation**: URIs must match the client's configured instance.
3. **None Returns**: Methods return `None` when an entity is not found, rather than raising an exception.

## Comparison to ResultContainer API

If you find yourself needing any of the following, consider using {doc}`resultcontainer_api` instead:

- Working with raw dictionary data
- Exporting directly to DataFrames without entity overhead
- Simple queries without relationships

## Entity-Specific Features

For detailed information about specific entity types and their special features (like `Dataset` export methods, `Workunit` parameter access, `Resource` path methods), see {doc}`../working_with_entities/index`.
