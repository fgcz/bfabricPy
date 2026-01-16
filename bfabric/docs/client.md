# Creating a Client

The `Bfabric` class provides the main interface for interacting with the B-Fabric system. Choose the appropriate
client creation method based on your use case:

## Choose Your Approach

```{toctree}
:maxdepth: 1
client_scripted
client_server
```

- **{doc}`client_scripted`** - For interactive sessions and scripts using config files
- **{doc}`client_server`** - For web servers and webapps using token-based authentication

## Quick Reference

| Use Case                         | Method                                                  | Key Features                                      |
| -------------------------------- | ------------------------------------------------------- | ------------------------------------------------- |
| Interactive scripts, local tools | `Bfabric.connect()`                                     | Config file auth, environment switching           |
| Web servers, webapps             | `Bfabric.connect_token()`                               | Token-based, async support, instance restrictions |
| Webapps with feeder users        | `Bfabric.connect_token()` + `WebappIntegrationSettings` | Elevated permissions, multi-instance support      |
