# Design Notes

Architectural decisions and design rationale for bfabricPy. Each page documents the *why* behind a module — the constraints that shaped it, alternatives that were considered, and the conventions future contributions are expected to follow.

These are contributor-facing references, not user guides. If you're looking for how to *use* a feature, start with [User Guides](../user_guides/index) or [Advanced Topics](../advanced_topics/index).

```{toctree}
:maxdepth: 1
operations_module
```

## Pages

| Topic | Scope |
| --- | --- |
| **[`bfabric.operations` Module](operations_module.md)** | Conventions and worked examples for named write capabilities (`create_workunit`, `create_dataset`, …), including the failure-cleanup pattern and the audit-vs-authorization split. |
