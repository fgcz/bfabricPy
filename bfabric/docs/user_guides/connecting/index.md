# Connecting

bfabricPy supports different authentication methods depending on your use case.

```{toctree}
:maxdepth: 1
interactive_scripted_usage
server_webapp_usage
```

## Choose Your Approach

| Use Case                                   | Method                                                     | Documentation                                               |
| ------------------------------------------ | ---------------------------------------------------------- | ----------------------------------------------------------- |
| Scripts, local tools, interactive sessions | `bfabric-cli login` once, then `Bfabric.connect()`         | [Interactive/Scripted Usage](interactive_scripted_usage.md) |
| Logging in from Python, without the CLI    | `Bfabric.connect_pkce()` / `Bfabric.connect_device_code()` | [Interactive/Scripted Usage](interactive_scripted_usage.md) |
| Non-interactive token                      | `Bfabric.connect_pat()`                                    | [Interactive/Scripted Usage](interactive_scripted_usage.md) |
| Background jobs, service accounts          | `Bfabric.connect_oauth()`                                  | [Server/Webapp Usage](server_webapp_usage.md)               |
| Webapps launched from B-Fabric             | `Bfabric.connect_token()` / `WebappClient.create()`        | [Server/Webapp Usage](server_webapp_usage.md)               |

## Next Steps

After connecting, learn how to work with B-Fabric:

- **[Reading Data](../reading_data/index.md)** - Query and retrieve data
- **[Writing Data](../writing_data/index.md)** - Create, update, and delete entities
- **[Working with Entities](../working_with_entities/index.md)** - Use typed entities and relationships

## See Also

- [CLI Authentication](../bfabric-cli/authentication.md) - `bfabric-cli auth` commands, scopes, multiple instances
- [Configuration Guide](../../getting_started/configuration.md) - Setting up config files
- [API Reference: Bfabric Client](../../api_reference/bfabric_client/index.md) - Complete client documentation
- [Error Handling](../error_handling.md) - Authentication errors
