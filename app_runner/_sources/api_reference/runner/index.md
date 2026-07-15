# Python Runner API

The programmatic entry point for executing an app's lifecycle. `run_app` runs the full
dispatch → inputs → process → collect → register sequence for a workunit; `Runner` exposes the
individual steps if you need finer control; `ChunksFile` describes the chunks discovered under a
work directory.

## When to use this vs. the CLI

`run_app` is what `bfabric-app-runner run workunit` calls under the hood. Most users should drive
the app runner through the [CLI](../../user_guides/cli_reference.md) — reach for this API only when
embedding execution in another Python program or orchestrator.

## run_app

```{eval-rst}
.. autofunction:: bfabric_app_runner.app_runner.runner.run_app
```

## Runner

Runs a single app version's steps against a work/chunk directory. Each method wraps one lifecycle
stage; `run_collect` is a no-op when the app version defines no `collect` command.

```{eval-rst}
.. autoclass:: bfabric_app_runner.app_runner.runner.Runner
    :members: run_dispatch, run_inputs, run_process, run_collect
```

## ChunksFile

Represents the `chunks.yml` in a work directory. `read` loads it (auto-discovering and writing it
when absent); `infer_from_directory` scans for subdirectories containing an `inputs.yml`.

```{eval-rst}
.. autoclass:: bfabric_app_runner.app_runner.runner.ChunksFile
    :members: infer_from_directory, read
```

## See Also

- [CLI Reference](../../user_guides/cli_reference.md) — `run workunit` and the per-step `action` commands
- [Architecture Overview](../../architecture/overview.md) — the dispatch → process → collect lifecycle
