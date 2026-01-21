# Entity Caching

Entity caching improves performance by storing entities in memory to avoid repeated API calls. This is particularly useful when
working with the same entities multiple times or navigating complex relationships.

## Overview

Caching is enabled through the `cache_entities()` context manager. Within the context, entities are cached according to your
configuration.

```{note}
Caching is an optional optimization feature. bfabricPy works perfectly without caching, but performance can be significantly
improved for complex operations.
```

## Basic Usage

### Cache a Single Entity Type

Enable caching for a specific entity type with an optional size limit:

```python
from bfabric import Bfabric
from bfabric.entities.cache.context import cache_entities

client = Bfabric.connect()
reader = client.reader

with cache_entities("sample", max_size=100):
    # First call fetches from API
    sample1 = reader.read_id(entity_type="sample", entity_id=123)

    # Second call uses cache (no API call)
    sample2 = reader.read_id(entity_type="sample", entity_id=123)

    # Both are the same object
    assert sample1 is sample2
```

### Unlimited Cache Size

Set `max_size=0` for unlimited cache size:

```python
with cache_entities("sample", max_size=0):
    # Cache as many samples as needed
    samples = reader.read_ids(entity_type="sample", entity_ids=list(range(1, 1000)))
```

### Cache Multiple Entity Types

Cache multiple entity types with the same size limit:

```python
with cache_entities(["sample", "project", "workunit"], max_size=500):
    # All three types are cached
    project = reader.read_id(entity_type="project", entity_id=1)
    samples = reader.read_ids(entity_type="sample", entity_ids=[1, 2, 3])
    workunits = reader.read_ids(entity_type="workunit", entity_ids=[10, 20])
```

### Different Sizes per Type

Configure different cache sizes for each entity type:

```python
cache_config = {
    "sample": 1000,  # Cache up to 1000 samples
    "project": 10,  # Cache up to 10 projects
    "workunit": 500,  # Cache up to 500 workunits
}

with cache_entities(cache_config):
    # Each type has its own size limit
    pass
```

## Advanced Usage

### Nested Contexts

Cache contexts can be nested. Inner contexts can override or extend outer ones:

```python
# Outer context caches samples
with cache_entities("sample", max_size=100):
    sample1 = reader.read_id(entity_type="sample", entity_id=1)

    # Inner context adds project caching
    with cache_entities("project", max_size=10):
        project = reader.read_id(entity_type="project", entity_id=1)
        # Sample is still cached from outer context
        sample2 = reader.read_id(entity_type="sample", entity_id=1)
        assert sample1 is sample2

    # Project cache is cleared, sample cache remains
    # project = reader.read_id(entity_type="project", entity_id=1)  # Would fetch from API
```

### Relationship Navigation

Caching is especially beneficial when navigating entity relationships:

```python
from bfabric import Bfabric
from bfabric.entities.cache.context import cache_entities

client = Bfabric.connect()
reader = client.reader

with cache_entities(["project", "sample", "workunit"], max_size=0):
    # Load project
    project = reader.read_id(entity_type="project", entity_id=123)

    # Navigate to samples (lazy-loaded)
    samples = project.refs.get("member")

    # Navigate to workunits for each sample
    for sample in samples:
        workunits = sample.refs.get("member")
        # Entities may be reused across relationships
        print(f"Sample {sample.id}: {len(workunits)} workunits")
```

In this example, the same entities might be accessed multiple times through different relationships. Caching ensures they're only
fetched once from the API.

## When to Use Caching

### Good Use Cases

- **Complex relationship navigation**: Traversing entity graphs (project → samples → workunits)
- **Repeated queries**: Same entities accessed multiple times in a workflow
- **Batch processing**: Loading entities once for multiple operations
- **Performance-sensitive operations**: When API latency impacts user experience

### When Caching May Not Help

- **One-off queries**: Loading each entity only once
- **Large datasets**: Memory may be more limiting than API speed
- **Frequently changing data**: When you always need fresh data

## Cache Behavior

### Cache Stack

bfabricPy uses a stack-based cache system. When you nest contexts, caches are layered:

```python
with cache_entities("sample", max_size=100):
    sample1 = reader.read_id(entity_type="sample", entity_id=1)

    with cache_entities("sample", max_size=10):
        sample2 = reader.read_id(entity_type="sample", entity_id=1)
        # Returns cached entity from outer context
        assert sample1 is sample2

        # New entities go to inner cache (limited to 10)
        sample3 = reader.read_id(entity_type="sample", entity_id=2)

    # Inner cache cleared, outer cache remains
```

### Cache Invalidation

Caches are automatically invalidated when the context exits:

```python
with cache_entities("sample", max_size=100):
    sample = reader.read_id(entity_type="sample", entity_id=1)
    # Sample is cached

# Cache is cleared here
sample = reader.read_id(entity_type="sample", entity_id=1)
# Sample fetched from API again
```

## Performance Considerations

### Memory vs Speed Trade-off

- **Small cache size**: Less memory, more API calls
- **Large cache size**: More memory, fewer API calls
- **Unlimited cache (`max_size=0`)**: Maximum speed, highest memory usage

### Choosing Cache Sizes

Consider:

- Number of entities you'll access
- Entity size (larger entities = more memory per entity)
- Available memory in your environment
- How often entities are reused

Example:

```python
# High-throughput scenario: larger caches
with cache_entities({"sample": 10000, "project": 100}, max_size=0):
    # Process thousands of entities efficiently
    pass

# Memory-constrained scenario: smaller caches
with cache_entities({"sample": 100, "project": 10}):
    # Keep memory usage low
    pass
```

## Complete Example

```python
from bfabric import Bfabric
from bfabric.entities.cache.context import cache_entities

client = Bfabric.connect()
reader = client.reader

# Configure caches for your workflow
cache_config = {
    "project": 50,  # Fewer projects, larger entities
    "sample": 1000,  # More samples, smaller entities
    "workunit": 5000,  # Many workunits, small entities
}

with cache_entities(cache_config):
    # Load a project
    project = reader.read_id(entity_type="project", entity_id=1)

    # Get all samples for the project
    samples = project.refs.get("member")

    print(f"Loaded {len(samples)} samples")

    # Process each sample
    for sample in samples:
        # Get workunits (may reuse workunits from other samples)
        workunits = sample.refs.get("member")
        print(f"Sample {sample.id}: {len(workunits)} workunits")

    # Entities are cached, so repeated accesses are fast
    project2 = reader.read_id(entity_type="project", entity_id=1)
    assert project is project2  # Same object, no API call
```

## Summary

- Use `cache_entities()` to enable entity caching within a context
- Configure cache sizes based on your memory and performance needs
- Caching is especially beneficial for relationship navigation and repeated access
- Cache contexts can be nested for fine-grained control
- Caches are automatically cleared when the context exits

## Advanced: Cache Internals

For details on cache implementation, see:

```{eval-rst}
.. automodule:: bfabric.entities.cache
    :members:
    :undoc-members:
    :show-inheritance:
```

This includes:

- `cache_entities()` - Context manager for enabling caching
- `EntityMemoryCache` - In-memory cache implementation
- `CacheStack` - Stack-based cache management

See {doc}`entity_reference` for complete documentation of all entity types and their features.
