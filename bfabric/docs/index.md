# bfabricPy Documentation

bfabricPy provides a Python interface to the [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/) system.

```{toctree}
:maxdepth: 2
:caption: Getting Started:
getting_started/index
getting_started/installation
getting_started/quick_start
getting_started/configuration
```

```{toctree}
:maxdepth: 2
:caption: User Guides:
user_guides/index
user_guides/creating_a_client/index
user_guides/reading_data/index
user_guides/writing_data/index
user_guides/working_with_entities/index
user_guides/cli_reference/index
```

## API Reference

Complete, auto-generated documentation from the code:

```{toctree}
:maxdepth: 2
:caption: API Reference:
api_reference/index
api_reference/bfabric_client/methods
api_reference/entity_types/index
api_reference/entity_reader/index
api_reference/result_container/index
api_reference/token_data/index
api_reference/exceptions_and_errors/index
```

## Advanced Topics

For experienced users:

```{toctree}
:maxdepth: 2
:caption: Advanced Topics:
advanced_topics/index
advanced_topics/token_authentication/index
advanced_topics/workunit_definitions/index
advanced_topics/experimental_features/index
```

## Resources

Additional resources and support:

```{toctree}
:maxdepth: 1
:caption: Resources:
resources/index
resources/error_handling
resources/best_practices
resources/troubleshooting
resources/contributing
resources/changelog
```

## Key Features

### Entity System

bfabricPy provides a rich entity system with typed classes, relationships, and special features:

- **20+ entity types** with auto-generated documentation
- **Relationships**: Navigate connected entities (project → samples → workunits)
- **Special features**: Dataset exports, Workunit parameters, Resource paths
- **URI support**: Reference entities across B-Fabric instances
- **Automatic caching**: Performance optimization for repeated access

### Dual API Design

bfabricPy provides two complementary APIs:

| Feature       | ResultContainer API           | Entity API                           |
| ------------- | ----------------------------- | ------------------------------------ |
| Use Case      | Simple queries, data analysis | Working with entities, relationships |
| Entry Point   | `client.read(endpoint, obj)`  | `client.reader`                      |
| Return Type   | Dictionaries (raw data)       | Entity objects (typed)               |
| Relationships | Manual handling               | Lazy-loading via `entity.refs`       |
| Caching       | Manual                        | Automatic (via `cache_entities()`)   |

### Authentication Methods

- **Config-based**: For scripts and interactive sessions
- **Token-based**: For web servers and webapps
- **Async support**: For async frameworks (FastAPI, asyncio)

### Experimental Features

- Dataset upload from CSV
- Custom attributes update
- Workunit definitions (YAML)
- Entity caching context

## Installation

```bash
# Install library
pip install bfabric

# Install command-line tools
uv tool install bfabric-scripts
```

See [Installation Guide](getting_started/installation.md) for more options.

## Documentation Structure

This documentation is organized by **what you want to do** rather than by API structure:

- **[Getting Started](getting_started/index)** - Installation, configuration, first script
- **[User Guides](user_guides/index)** - Task-based tutorials and examples
- **[API Reference](api_reference/index)** - Complete, auto-generated documentation
- **[Advanced Topics](advanced_topics/index)** - Advanced features and patterns
- **[Resources](resources/index)** - Error handling, best practices, contributing

## Contributing

Contributions are welcome! See [Contributing Guide](resources/contributing.md) for details.

## Version

Current version and history: [Changelog](resources/changelog.md)

## License

Copyright (C) 2014-2026 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Licensed under GPL version 3.

## Support

- **Issues**: https://github.com/fgcz/bfabricPy/issues
- **Documentation**: https://github.com/fgcz/bfabricPy
