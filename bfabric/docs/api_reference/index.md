# API Reference

Complete API documentation for all bfabricPy classes and methods.

```{toctree}
:maxdepth: 1
bfabric_client/index
entity_types/index
entity_reader/index
entity_uri/index
result_container/index
token_data/index
exceptions_and_errors/index
```

## Documentation Style

This section uses **auto-generated documentation** directly from the Python code using Sphinx autodoc and autodoc_pydantic extensions. This ensures:

✅ Documentation is always in sync with the code
✅ Type signatures are accurate
✅ Parameters and return types are complete
✅ No redundant manual maintenance

## Quick Links

| Component | Description |
| --------------------------------------------------------- | -------------------------------------------------- |
| **[Bfabric Client](bfabric_client/index.md)** | Main client class with all read/write methods |
| **[Entity Types](entity_types/index.md)** | All 20+ entity types with auto-documented features |
| **[EntityReader](entity_reader/index.md)** | Entity-based reading with caching support |
| **[EntityUri](entity_uri/index.md)** | Entity identifier across instances |
| **[ResultContainer](result_container/index.md)** | Query result container with error handling |
| **[Token Data](token_data/index.md)** | Token authentication data structure |
| **[Exceptions & Errors](exceptions_and_errors/index.md)** | All exception types and when they're raised |

## For Beginners

If you're new to bfabricPy, start with:

1. [Quick Start Tutorial](../../getting_started/quick_start.md) - 5-minute tutorial
2. [User Guides](../../user_guides/index.md) - Task-based guides
3. Then return here for detailed API reference

## Finding What You Need

### By Task

| Task | Relevant Documentation |
| ------------------ | -------------------------------------------------------------------------------------------- |
| Create a client | [Bfabric Client](bfabric_client/index.md), [Getting Started](../../getting_started/index.md) |
| Query B-Fabric | [Bfabric Client: read()](bfabric_client/index.md), [EntityReader](entity_reader/index.md) |
| Work with entities | [Entity Types](entity_types/index.md), [EntityReader](entity_reader/index.md) |
| Write data | [Bfabric Client: save()](bfabric_client/index.md) |
| Handle errors | [Exceptions & Errors](exceptions_and_errors/index.md) |

### By Class

| Class | What It Does |
| --------------------- | ------------------------------------ |
| `Bfabric` | Main client - all API operations |
| `Entity` | Base class for all B-Fabric entities |
| `EntityReader` | Read entities by URI/ID/query |
| `ResultContainer` | Container for query results |
| `EntityUri` | Entity identifier across instances |
| `TokenData` | Token authentication data |
| `BfabricRequestError` | Server-side errors |
| `BfabricConfigError` | Configuration errors |

## API Stability

bfabricPy follows semantic versioning (`X.Y.Z`):

- **Major changes (X)**: May include breaking changes, announced in changelog
- **Minor changes (Y)**: New features, backward compatible
- **Patch changes (Z)**: Bug fixes, backward compatible

For version history and deprecation notices, see [Changelog](../../resources/changelog.md).

## Contributing to Documentation

Documentation is generated from docstrings in the code. To improve it:

1. **Add docstrings** to public classes, methods, and functions
2. **Update docstrings** when changing behavior
3. **Run documentation build** to see changes
4. **Commit documentation** changes along with code changes

See [Contributing Guide](../../../CONTRIBUTING.md) for more details.

## Next Steps

- [Bfabric Client](bfabric_client/index.md) - Start with main client documentation
- [Entity Types](entity_types/index.md) - See all entity types
- [User Guides](../../user_guides/index.md) - Return to task-based guides
