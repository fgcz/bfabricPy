# Advanced Topics

Advanced features and topics for experienced users.

```{toctree}
:maxdepth: 1
token_authentication/index
workunit_definitions/index
experimental_features/index
```

## Topics Overview

| Topic                                                 | Description                                  | Skill Level  |
| ----------------------------------------------------- | -------------------------------------------- | ------------ |
| **[Token Authentication](token_authentication.md)**   | Deep dive into token-based auth for web apps | Advanced     |
| **[Workunit Definitions](workunit_definitions.md)**   | YAML-based workunit configuration            | Intermediate |
| **[Experimental Features](experimental_features.md)** | Cutting-edge features that may change        | Experimental |

## Advanced Guides

These guides assume familiarity with basic bfabricPy concepts:

- You've completed [Getting Started](../../getting_started/index.md)
- You're comfortable with [Reading Data](../../user_guides/reading_data/index.md)
- You've practiced [Writing Data](../../user_guides/writing_data/index.md)

## Experimental Features

```{warning}
Experimental features may change or be removed in future versions. Use at your own risk.
```

Experimental features are bleeding-edge functionality:

- **Dataset upload from CSV** - `bfabric_save_csv2dataset`
- **Custom attributes update** - `update_custom_attributes()`
- **Workunit definitions** - YAML-based workunit configuration
- **Entity caching** - `cache_entities()` context manager

See [Experimental Features](experimental_features.md) for details.

## Related Documentation

- [User Guides](../../user_guides/index.md) - Practical guides
- [API Reference](../../api_reference/index.md) - Complete API documentation
- [Changelog](../../resources/changelog.md) - Version history and changes
