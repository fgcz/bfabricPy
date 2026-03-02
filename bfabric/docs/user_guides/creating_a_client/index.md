# Creating a Client

bfabricPy supports different authentication methods depending on your use case.

```{toctree}
:maxdepth: 1
interactive_scripted_usage
server_webapp_usage
```

## Choose Your Approach

| Use Case | Method | Documentation |
| ------------------------------------------ | ------------------------------------ | ------------------------------------------------------------- |
| Scripts, local tools, interactive sessions | `Bfabric.connect()` with config file | [Interactive/Scripted Usage](interactive_scripted_usage.md) |
| Web servers, web apps, token-based auth | `Bfabric.connect_token()` with token | [Server/Webapp Usage](server_webapp_usage.md) |

## Next Steps

After creating your client, learn how to work with B-Fabric:

- **[Reading Data](../reading_data/index.md)** - Query and retrieve data
- **[Writing Data](../writing_data/index.md)** - Create, update, and delete entities
- **[Working with Entities](../working_with_entities/index.md)** - Use typed entities and relationships

## See Also

- [Configuration Guide](../../getting_started/configuration.md) - Setting up config files
- [API Reference: Bfabric Client](../../api_reference/bfabric_client/index.md) - Complete client documentation
- [Error Handling](../error_handling.md) - Authentication errors
