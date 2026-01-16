# Reading Data

bfabricPy provides two complementary APIs for reading data from B-Fabric, depending on your needs:

## Choose Your Approach

```{toctree}
:maxdepth: 1
read_resultcontainer
read_entity_api
read_caching
```

- **{doc}`read_resultcontainer`** - Direct queries returning raw data structures
- **{doc}`read_entity_api`** - Entity objects with lazy-loaded relationships
- **{doc}`read_caching`** - Performance optimization through entity caching

## Quick Comparison

| Feature           | ResultContainer API           | Entity API                           |
| ----------------- | ----------------------------- | ------------------------------------ |
| **Primary Class** | `ResultContainer`             | `EntityReader` / `Entity`            |
| **Entry Point**   | `client.read(endpoint, obj)`  | `client.reader`                      |
| **Return Type**   | Dictionaries (raw API data)   | Entity objects                       |
| **Relationships** | Manual handling               | Lazy-loading via `entity.refs`       |
| **Caching**       | Manual                        | Automatic (via `cache_entities()`)   |
| **URI Support**   | Limited                       | Full URI-based access                |
| **Data Export**   | Polars DataFrames             | Via `data_dict`                      |
| **Use Case**      | Simple queries, data analysis | Working with entities, relationships |

## ResultContainer API

Use this when you need to:

- Perform simple queries and work with raw data
- Export results to DataFrames (Polars)
- Have full control over data structure
- Don't need entity relationships

Access via `client.read(endpoint, obj)` which returns a `ResultContainer`.

## Entity API

Use this when you need to:

- Work with typed entity objects
- Navigate relationships (e.g., project → samples → workunits)
- Use URIs to reference entities
- Leverage automatic caching with `cache_entities()`
- Maintain object identity across code

Access via `client.reader` which provides methods like `read_uri()`, `read_id()`, `query()`.
