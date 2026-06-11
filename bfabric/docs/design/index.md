# Design Notes

Architectural decisions and design rationale for bfabricPy. Each page documents the *why* behind a module — the constraints that shaped it, alternatives that were considered, and the conventions future contributions are expected to follow.

These are contributor-facing references, not user guides. If you're looking for how to *use* a feature, start with [User Guides](../user_guides/index) or [Advanced Topics](../advanced_topics/index).

```{toctree}
:maxdepth: 1
operations_module
oauth_integration
```

## Pages

| Topic | Scope |
| --- | --- |
| **[`bfabric.operations` Module](operations_module.md)** | Conventions and worked examples for named write capabilities (`create_workunit`, `create_dataset`, …), including the failure-cleanup pattern and the audit-vs-authorization split. |
| **[OAuth Integration](oauth_integration.md)** | The `bfabric._oauth` module and OAuth 2.0 flows (PKCE, device code, client credentials, URL token, PAT), the `Bfabric.connect_*` factory methods, `bfabric-cli auth` commands, and the config/scope model. |
