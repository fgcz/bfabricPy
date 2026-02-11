# Bfabric Client API Reference

Complete API reference for the `Bfabric` client class, automatically generated from source code documentation.

## Quick Links

- **[Creating a Client](../../user_guides/creating_a_client/index.md)** - Step-by-step guides for different use cases
- **[Configuration](../../getting_started/configuration.md)** - Config file setup and options
- **[Quick Start](../../getting_started/quick_start.md)** - 5-minute tutorial

## API Overview

The `Bfabric` class provides methods for:

| Category | Methods |
|----------|---------|
| Client Creation | `connect()`, `connect_token()`, `from_token_data()` |
| Read Operations | `read()`, `exists()` |
| Write Operations | `save()`, `delete()`, `upload_resource()` |
| Configuration | `config`, `auth`, `config_data` properties |
| Entity Operations | `reader` property for `EntityReader` |
| Context Management | `with_auth()` |

______________________________________________________________________

## Bfabric Class

```{eval-rst}
.. autoclass:: bfabric.Bfabric
    :members: connect, from_config, from_token_data, connect_webapp, connect_token, connect_token_async, read, save, delete, exists, upload_resource, with_auth, config, auth, config_data, reader
    :undoc-members:
    :show-inheritance:
```

### Client Creation Methods

#### For Interactive/Scripted Usage

```{eval-rst}
.. automethod:: bfabric.Bfabric.connect
```

#### Deprecated Methods

```{eval-rst}
.. automethod:: bfabric.Bfabric.from_config
.. automethod:: bfabric.Bfabric.connect_webapp
```

#### For Server/Webapp Usage

```{eval-rst}
.. automethod:: bfabric.Bfabric.connect_token
```

```{eval-rst}
.. automethod:: bfabric.Bfabric.from_token_data
```

### Read Operations

```{eval-rst}
.. automethod:: bfabric.Bfabric.read
```

```{eval-rst}
.. automethod:: bfabric.Bfabric.exists
```

### Write Operations

```{eval-rst}
.. automethod:: bfabric.Bfabric.save
```

```{eval-rst}
.. automethod:: bfabric.Bfabric.delete
```

```{eval-rst}
.. automethod:: bfabric.Bfabric.upload_resource
```

### Configuration and Authentication

```{eval-rst}
.. autoattribute:: bfabric.Bfabric.config
```

```{eval-rst}
.. autoattribute:: bfabric.Bfabric.auth
```

```{eval-rst}
.. autoattribute:: bfabric.Bfabric.config_data
```

### Context Management

```{eval-rst}
.. automethod:: bfabric.Bfabric.with_auth
```

### EntityReader Access

```{eval-rst}
.. autoattribute:: bfabric.Bfabric.reader
```

## Related Documentation

- [User Guides](../../user_guides/index.md) - Practical usage examples
- [Getting Started](../../getting_started/index.md) - Setup and basics
