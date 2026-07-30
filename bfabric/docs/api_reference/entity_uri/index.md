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

The instance must be served over `https`; `http` is accepted for `localhost` only (development
instances).

The constructor is strict: it accepts exactly this canonical form. To accept a URL as a user copied
it out of the browser, use [`from_web_url`](#normalize-a-web-url).

### Key Features

- **Validation**: Automatic validation of URI format and structure
- **Parsing**: Extract entity type and ID from URIs
- **Construction**: Create URIs from components
- **Normalization**: Turn a B-Fabric web URL into the canonical URI
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

(normalize-a-web-url)=
### Normalize a Web URL

A URL copied from the browser usually carries extra query parameters (e.g. the selected tab), which
the constructor rejects. `EntityUri.from_web_url` normalizes it instead:

```python
from bfabric.entities.core.uri import EntityUri

uri = EntityUri.from_web_url(
    "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=346001&tab=details"
)
print(uri)  # "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=346001"
```

Dropped: every query parameter except `id`, and the fragment. Normalized: host case and a default
port (`:443` on `https`). Everything else is still validated as strictly as in the constructor — the
path must be `/bfabric/<entity_type>/show.html`, and `id` must be present exactly once (repeated
`id` parameters with conflicting values are an error) and a positive integer.

Because the result is canonical, it compares and hashes equal to the same entity's `EntityUri`, so a
pasted URL can be used as an `EntityResult` or cache key.

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
