# Bfabric Client

Complete reference for the `Bfabric` client class.

```{toctree}
:maxdepth: 1
overview
configuration
methods
```

## Overview

The `Bfabric` class is the main entry point for all bfabricPy operations.

### Quick Start

```python
from bfabric import Bfabric

# Create client (uses ~/.bfabricpy.yml)
client = Bfabric.connect()

# Use the client
projects = client.read(endpoint="project", obj={}, max_results=10)
for project in projects:
    print(project["name"])
```

### Client Properties

```python
client = Bfabric.connect()

# Access configuration
print(client.config.base_url)  # B-Fabric instance URL
print(client.config.engine)  # "zeep" or "suds"
print(client.auth.login)  # User login
```

### Accessing EntityReader

```python
# Get EntityReader for entity-based operations
reader = client.reader

# Read entities as typed objects
project = reader.read_id(entity_type="project", entity_id=123)
```

## See Also

- [Configuration](configuration.md) - Client configuration options
- [Methods](methods.md) - All read/write methods
- [Creating a Client Guide](../../../user_guides/creating_a_client/index.md) - Choose authentication method
