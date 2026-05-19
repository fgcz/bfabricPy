# Design Notes: Generic Dataset Flow Dispatch

## Motivation

Replace per-app custom dispatch scripts with one built-in dispatcher.
The app author declares a dataset-flow config and gets: downloaded files + dataset parquet + `params.yml` automatically staged in the chunk directory — no bespoke Python needed.

## Decisions

- New discriminated `Command` type (`type: dataset_flow`) in `CommandsSpec`; `runner.run_dispatch()` detects it and calls the built-in directly, bypassing `execute_command`.
- Single chunk for v1; external executors handle distribution across folders if needed.
- The collect step is also built-in when dispatch is `dataset_flow` — no separate collect command required.
- Output dataset is **enforced**: the process command must produce a dataset file at a known location or the collect step fails with a clear error.

## Command spec shape (app.yml)

```yaml
commands:
  dispatch:
    type: dataset_flow
    input:
      column: Resource          # column name or index containing resource IDs
      include_patterns: []      # glob filters applied during extraction
      exclude_patterns: []
      check_checksum: true
    output:
      expected_filename: "output/dataset.parquet"   # MUST be produced by process
      dataset_name: "{workunit.name} – results"     # optional name override
  process:
    type: exec
    command: "python run.py"
  # collect is omitted — built-in collect runs automatically
```

## Chunk layout (contract with the process command)

```
chunk_dir/
  input/
    dataset.parquet        # input dataset with added "File" column
    <downloaded files>
  params.yml               # raw workunit parameters only (dict, no envelope)
  workunit.yml             # metadata envelope: workunit_id, container_id, application_id, user
  output/                  # created by dispatch; process command writes here
    dataset.parquet        # REQUIRED — enforced by built-in collect
    <produced files>       # referenced by the output dataset's file column
```

`params.yml` contains only the raw parameter dict. `workunit.yml` is the escape hatch
for apps that need workunit/container metadata for registration purposes — kept separate
to avoid coupling params and metadata.

## Built-in dispatch (`dispatch/builtin_dataset_flow.py`)

1. Load `WorkunitDefinition`, resolve input dataset id.
2. Emit single chunk `work/` with `inputs.yml` containing:
   - `BfabricResourceDatasetSpec` (filename=`input`, populated from `spec.input`).
   - `StaticYamlSpec` → `params.yml` (raw params dict).
   - `StaticYamlSpec` → `workunit.yml` (metadata envelope).
3. `mkdir chunk/output` so the process command has a target.
4. `write_chunks_file(work_dir, [Path("work")])`.

No new resolver required — `BfabricResourceDatasetSpec` already has one.

## Built-in collect (`collect/builtin_dataset_flow.py`)

1. Assert `chunk_dir / spec.output.expected_filename` exists — hard fail with clear message if not.
2. Read the output dataset (parquet or CSV, detected by suffix) to enumerate the file column.
3. Emit `outputs.yml` containing:
   - One `SaveDatasetSpec` pointing at the output dataset file.
   - One `CopyResourceSpec` per file referenced by the dataset's file column.
4. Existing outputs pipeline handles registration.

## Known issues to resolve

- `SaveDatasetSpec` currently fails if the workunit already has an output dataset
  (TODO at `specs/outputs_spec.py:40`). Since this flow always writes one, the underlying
  save logic needs to support update-in-place or delete-and-replace. Expose as
  `spec.output.update_existing: Literal["replace", "error"]`.

## Scope (v1)

- Single chunk only.
- Input must be a B-Fabric dataset (`BfabricResourceDatasetSpec`) — apps needing
  single-resource or archive inputs keep custom dispatches.
- No automatic merging of input and output datasets — the app handles that.
- All existing custom-dispatch code paths remain intact; this is purely additive.

## Files to create / modify

| File | Change |
|------|--------|
| `specs/app/commands_spec.py` | Add `CommandDispatchDatasetFlow` to `Command` union |
| `dispatch/builtin_dataset_flow.py` | New — built-in dispatch logic |
| `collect/builtin_dataset_flow.py` | New — built-in collect logic |
| `app_runner/runner.py` | Detect `dataset_flow` type in `run_dispatch()`, skip `execute_command` |
| `specs/outputs_spec.py` | Fix `SaveDatasetSpec` update-existing behaviour |

## Tests

- Dispatch: spec parsing, dataset ID resolution, `inputs.yml` shape, `params.yml`/`workunit.yml` contents, `output/` created.
- Collect: missing output dataset → clear error; valid output → correct `outputs.yml` structure.
- End-to-end with mocked `Bfabric` client and a toy dataset.
