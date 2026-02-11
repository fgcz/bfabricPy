# API Reference: EntityUri

Complete reference for entity URI classes.

```{eval-rst}
.. autoclass:: bfabric.entities.core.uri.EntityUri
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.core.uri.EntityUriComponents
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.core.uri.GroupedUris
    :members:
    :show-inheritance:
```

## Overview

The `EntityUri` system provides validated entity identifiers that work across B-Fabric instances.

### URI Format

B-Fabric entity URIs follow this pattern:

```
https://<instance>/bfabric/<entity_type>/show.html?id=<id>
```

Example: `https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123`

### Key Features

- **Validation**: Automatic validation of URI format and structure
- **Parsing**: Extract entity type and ID from URIs
- **Construction**: Create URIs from components
- **Cross-instance**: Reference entities from any B-Fabric instance

## Usage Examples

### Parse Existing URI

```python
from bfabric.entities.core.uri import EntityUri

# Parse URI from string
uri = EntityUri("https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123")

# Access components
print(uri.components.bfabric_instance)  # "https://fgcz-bfabric.uzh.ch/bfabric/"
print(uri.components.entity_type)  # "sample"
print(uri.components.entity_id)  # 123
```

### Construct URI from Components

```python
from bfabric.entities.core.uri import EntityUri

# Build URI from parts
uri = EntityUri.from_components(
    bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
    entity_type="sample",
    entity_id=123,
)
print(uri)  # "https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123"
```

### With EntityReader

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read by URI
uri = EntityUri("https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123")
sample = reader.read_uri(uri)
```

### Read Multiple URIs

```python
from bfabric.entities.core.uri import EntityUri

uris = [
    "https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=123",
    "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=456",
]

entities = reader.read_uris(uris)
```

## URI Format Details

### Component Breakdown

| Component | Description | Example |
|-----------|-------------|---------|
| `bfabric_instance` | Base URL of B-Fabric instance | `https://fgcz-bfabric.uzh.ch/bfabric/` |
| `entity_type` | Entity name (lowercase) | `sample`, `project`, `workunit` |
| `entity_id` | Numeric entity ID | `123` |

### Supported Entity Types

All lowercase B-Fabric entity types are valid:

- `sample`, `project`, `order`, `container`
- `workunit`, `dataset`, `resource`
- `application`, `executable`, `parameter`
- `workflow`, `workflowstep`
- And all other B-Fabric entity types

## Error Handling

```python
from bfabric.entities.core.uri import EntityUri

try:
    # Invalid URI
    uri = EntityUri("https://example.com/invalid")
except ValueError as e:
    print(f"Invalid URI: {e}")
```

## See Also

- [Working with Entities](../../user_guides/working_with_entities/index.md) - Guide to entity operations
- [EntityReader](../entity_reader/index.md) - Reading entities by URI
