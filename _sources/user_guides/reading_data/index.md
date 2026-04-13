# Reading Data

Learn to query B-Fabric and retrieve data using different approaches.

```{toctree}
:maxdepth: 1
resultcontainer_api
entity_api
caching_for_performance
```

## Choose Your Approach

bfabricPy provides two complementary APIs for reading data:

| Approach | Primary Class | Best For | Documentation |
| ----------------------- | ------------------------- | ----------------------------------------------- | --------------------------------------------- |
| **ResultContainer API** | `ResultContainer` | Simple queries, data analysis, DataFrame export | [ResultContainer API](resultcontainer_api.md) |
| **Entity API** | `Entity` / `EntityReader` | Typed entities, relationships, URI access | [Entity API](entity_api.md) |

## Quick Comparison

| Feature | ResultContainer API | Entity API |
| ----------------- | ----------------------------- | ------------------------------------ |
| **Entry Point** | `client.read(endpoint, obj)` | `client.reader` |
| **Return Type** | Dictionaries (raw data) | Entity objects (typed) |
| **Relationships** | Manual handling | Lazy-loading via `entity.refs` |
| **Caching** | Manual | Automatic (via `cache_entities()`) |
| **URI Support** | Limited | Full URI-based access |
| **Data Export** | Polars DataFrames | Via `data_dict` |
| **Use Case** | Simple queries, data analysis | Working with entities, relationships |

## See Also

- [Working with Entities](../working_with_entities/index.md) - Entity type reference
- [API Reference: EntityReader](../../api_reference/entity_reader/index.md) - Complete EntityReader documentation
- [Error Handling](../error_handling.md) - Query error handling
