# Design Notes

Design rationale for parts of bfabricPy whose shape is non-obvious from the code alone. These pages explain *why* a module looks the way it does — the constraints, alternatives considered, and the conventions that future contributions are expected to follow.

These are contributor-facing references, not user guides. If you're looking for how to *use* a feature, start with [User Guides](../user_guides/index) or [Advanced Topics](../advanced_topics/index).

```{toctree}
:maxdepth: 1
operations_module
```

## Pages

| Topic | Scope |
| --- | --- |
| **[`bfabric.operations` Module](operations_module.md)** | Conventions and worked examples for named write capabilities (`create_workunit`, `create_dataset`, …), including the failure-cleanup pattern and the audit-vs-authorization split. |
