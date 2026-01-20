# Entity System

bfabricPy provides a comprehensive entity system for working with B-Fabric objects, with typed entity classes, relationships, and rich features.

## Choose Your Approach

```{toctree}
:maxdepth: 1
entity_reference
read_resultcontainer
read_entity_api
read_caching
```

- **{doc}`entity_reference`** - Complete reference for all entity types, their features, and relationships
- **{doc}`read_entity_api`** - Guide to reading entities using EntityReader with examples
- **{doc}`read_resultcontainer`** - Direct queries returning raw data structures
- **{doc}`read_caching`** - Performance optimization through entity caching

## Quick Comparison

| Feature           | Entity API                           | ResultContainer API           |
| ----------------- | ------------------------------------ | ----------------------------- |
| **Primary Class** | `EntityReader` / `Entity`            | `ResultContainer`             |
| **Entry Point**   | `client.reader`                      | `client.read(endpoint, obj)`  |
| **Return Type**   | Entity objects                       | Dictionaries (raw API data)   |
| **Relationships** | Lazy-loading via `entity.refs`       | Manual handling               |
| **Caching**       | Automatic (via `cache_entities()`)   | Manual                        |
| **URI Support**   | Full URI-based access                | Limited                       |
| **Data Export**   | Via `data_dict`                      | Polars DataFrames             |
| **Use Case**      | Working with entities, relationships | Simple queries, data analysis |

## Entity API

Use this when you need to:

- Work with typed entity objects
- Navigate relationships (e.g., project → samples → workunits)
- Use URIs to reference entities
- Leverage automatic caching with `cache_entities()`
- Maintain object identity across code

Access via `client.reader` which provides methods like `read_uri()`, `read_id()`, `query()`.

For a complete reference of all entity types and their features, see {doc}`entity_reference`.

## ResultContainer API

Use this when you need to:

- Perform simple queries and work with raw data
- Export results to DataFrames (Polars)
- Have full control over data structure
- Don't need entity relationships

Access via `client.read(endpoint, obj)` which returns a `ResultContainer`.
