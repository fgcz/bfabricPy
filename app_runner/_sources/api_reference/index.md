# API Reference

Orientation hub for the bfabric-app-runner API. An app is described by three YAML specs plus a
Python execution API:

- **App spec** (`app.yml`) — the app's versions and its `dispatch`/`process`/`collect` commands.
- **Input spec** (`inputs.yml`) — the files an app needs and where to fetch them.
- **Output spec** (`outputs.yml`) — the artifacts an app produces and how to register them.
- **Python runner API** — `Runner` / `run_app`, for driving the lifecycle programmatically.

Each spec page below is the canonical, field-by-field reference for its models. For how the pieces
fit together in the dispatch → process → collect lifecycle, see the
[Architecture Overview](../architecture/overview.md).

```{toctree}
:maxdepth: 1
runner/index
```

## Where to look

| To… | See |
| --- | --- |
| Define an app's versions and commands (`app.yml`) | [App specification](../specs/app_specification.md) |
| Declare and fetch input files (`inputs.yml`) | [Input specification](../specs/input_specification.md) |
| Register outputs back to B-Fabric (`outputs.yml`) | [Output specification](../specs/output_specification.md) |
| Run the lifecycle from the shell | [CLI Reference](../user_guides/cli_reference.md) |
| Drive the lifecycle from Python | [Python runner API](runner/index.md) |
