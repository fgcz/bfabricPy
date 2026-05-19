# `bfabric.operations.analysis_result` — Design Note

> **Status:** exploratory. Not yet implemented. Lives in `_design_notes/` until the shape is settled and a first version lands; then graduates to `design/`.

## What this is

A multi-entity write capability: given a description of a completed analysis, register it into B-Fabric as a workunit with its attached dataset, resources, and links — in one orchestrated call with shared failure cleanup.

A canonical on-disk format for the same thing, so that producers (CLI scripts, schedulers, app runners) and consumers (registration code) agree on a single serialization.

## Why this exists

Today the same orchestration is reimplemented in at least three places:

- `btools/register_custom_analysis.py` and `btools/register_sushi_dataset_into_bfabric.py` (folder convention + `dataset.tsv` with `[File]`/`[Link]`/`[Html]` column tags) — outside bfabricPy.
- `bfabric_app_runner.output_registration` (`OutputsSpec` YAML driving `register_file_in_workunit` + `_save_dataset` + `_save_link`).
- Ad-hoc compositions in pipeline scripts.

Each of these does the same conceptual work: create a workunit, attach a dataset, register resource files, add links, set status. Each has its own on-disk schema, its own failure handling, and its own audit-stamping conventions.

`bfabric.operations.analysis_result` consolidates the orchestration. Existing consumers become *callers* of one primitive instead of parallel reimplementations.

## Inclusion criterion (why it belongs in `bfabric.operations`)

Same test as `operations_module.md`:

- **Write capability against B-Fabric** — yes, it composes existing `create_workunit`, `create_dataset`, resource/link saves into one orchestrated call.
- **Deployment-agnostic** — yes, the operation takes already-resolved data. It does not know about `/srv/gstore/projects/p<ID>/` paths, `dataset.tsv` parsing, scp, checksumming, or any deployment-specific input format.

What stays out: file-path-to-payload resolution (btools' folder walk, app_runner's scp), TSV/YAML/folder-convention parsing, authorization, UI/prompting.

## Why it's its own module, not under `workunit/`

The natural reading of `bfabric/operations/workunit/format.py` is "the on-disk shape of a workunit." But the real artifact spans entities — workunit + dataset + resources + links. Nesting it under `workunit/` makes a reader expect workunit-shaped content and find more.

`analysis_result` sits at the top level of `bfabric.operations` alongside the per-entity domains. The name describes what it *is* (the output of an analysis run, ready to be registered); the function name describes what we *do* (`register_analysis_result`).

## Shape

```
bfabric/operations/
  workunit.py
  dataset/
  update_custom_attributes.py
  analysis_result.py   ← new
```

```python
# bfabric/operations/analysis_result.py
from pydantic import BaseModel

from bfabric import Bfabric
from bfabric.operations.dataset import CreateDatasetParams
from bfabric.operations.workunit import CreateWorkunitParams


class ResourceSpec(BaseModel):
    name: str
    base64: str  # already-resolved payload; caller produces this
    # Future: optional checksum, size, etc. if SOAP starts accepting them.


class LinkSpec(BaseModel):
    name: str
    url: str


class AnalysisResult(BaseModel):
    workunit: CreateWorkunitParams
    dataset: CreateDatasetParams | None = None
    dataset_table: "pl.DataFrame | None" = None  # if dataset is set
    resources: list[ResourceSpec] = []
    links: list[LinkSpec] = []
    model_config = {"arbitrary_types_allowed": True}


class AnalysisResultRecord(BaseModel):
    workunit_id: int
    dataset_id: int | None
    resource_ids: list[int]
    # The ids callers actually want back.


def register_analysis_result(
    client: Bfabric,
    result: AnalysisResult,
    audit_attributes: dict[str, str] | None = None,
) -> AnalysisResultRecord: ...
```

## Orchestration and failure cleanup

The composition extends the per-operation cleanup pattern from `operations_module.md` over more steps:

```python
workunit_id = _create_workunit_initial(client, result.workunit, audit_attributes or {})
try:
    dataset_id = None
    if result.dataset is not None:
        dataset_id = _create_dataset_attached(
            client,
            result.workunit_id := workunit_id,
            result.dataset,
            result.dataset_table,
        ).id
    resource_ids = _attach_resources(client, workunit_id, result.resources)
    _attach_links(client, workunit_id, result.links)
    _complete_workunit(client, workunit_id)
    return AnalysisResultRecord(
        workunit_id=workunit_id, dataset_id=dataset_id, resource_ids=resource_ids
    )
except BaseException:
    try:
        client.save("workunit", {"id": workunit_id, "status": "failed"})
    except BaseException as e:
        logger.error(f"Cleanup failed for workunit {workunit_id}: {e!r}")
    raise
```

Same three load-bearing properties:

- Outer `except BaseException` for KeyboardInterrupt-safety.
- Inner try/except on cleanup that logs but does not re-raise.
- No attempt to delete already-created child entities (dataset, resources). Partial state stays visible for diagnosis; the failed-status mark is the signal.

## On-disk format

Serialize `AnalysisResult` via Pydantic's `model_dump_json` / `model_validate_json` (or YAML). The schema is the Pydantic model; there is no separate hand-written spec.

That gives:

- A canonical filename convention (e.g., `analysis_result.yaml`) that consumers can produce and registration code can consume without a custom parser.
- Forward-compatible: adding optional fields to `AnalysisResult` doesn't break existing files.
- The format describes the *intent to register*, not the post-registration state. There is no write-back of "we created workunit_id=123" to the file — callers receive `AnalysisResultRecord` from the function and can log/persist the IDs as they wish.

What the format does **not** carry: paths on disk. Resources are `name + base64`, already resolved. The producer is responsible for materializing files into payloads before the file is written. btools-style folder conventions and app_runner-style scp configs stay on the producer side.

## Deferred consumer migrations

Once `register_analysis_result` lands, two existing consumers become migration targets — but not in the first PR:

- **btools `register_custom_analysis.py` and `register_sushi_dataset_into_bfabric.py`** become CLI wrappers that parse `dataset.tsv` + folder convention into an `AnalysisResult`, then call `register_analysis_result`. The `[File]`/`[Link]`/`[Html]` column-tag parsing stays in btools.
- **`bfabric_app_runner.output_registration`** converts `OutputsSpec` into an `AnalysisResult` and calls `register_analysis_result`. The scp + checksum logic stays in app_runner (resource resolution).

If `AnalysisResult` ships in a shape that fits btools but not app_runner (or vice versa), that's a design failure — a third parallel implementation rather than consolidation. The first PR should validate the shape against both before merging.

## Open questions

- **Resource payload shape.** Today `create_workunit` takes `resources: dict[str, str]` (name → base64). For larger files, that's wrong — SOAP can't carry GB of base64. The real registration path goes through scp + a `resource` row pointing to the storage location. `ResourceSpec` will likely need a discriminated union (`InlineResourceSpec` with base64, `StoredResourceSpec` with storage_id + relative_path + checksum). Decide before phase 4 lands; the wrong shape forces a breaking change later.
- **Dataset payload coupling.** `AnalysisResult.dataset_table: pl.DataFrame` is convenient for in-process producers but awkward to serialize. If the on-disk format is meant to be portable, the dataset content needs to live as a separate CSV/Parquet file referenced from the YAML, not embedded. This is the same problem as resource payloads.
- **Audit attributes — caller-supplied or schema field?** `create_workunit` takes `audit_attributes` as a function parameter. `register_analysis_result` could either follow that pattern, or move it into `AnalysisResult` as a field. The latter makes the on-disk format self-contained (the file says who created it). The former keeps audit identity at the call site (the consumer stamps it). Probably both: a field with the value the producer wrote, that the consumer can override.
- **One workunit per result, or many?** btools registers one workunit per folder. app_runner registers one workunit per dispatched job. Anything more elaborate (a parent workunit with child workunits) is out of scope for v1 — but worth noting we're not designing for it.
- **Failure on already-created workunit.** What if `register_analysis_result` is retried after the workunit was successfully created but a later step failed? Idempotency is deferred in `operations_module.md` ("Future possibilities") and the same deferral applies here. v1 leaves duplicates to the caller.

## Out of scope for v1

- Idempotent / resumable registration.
- Updating an existing analysis result (`update_analysis_result`).
- Cross-workunit dependencies (parent/child).
- A typed `AuditAttributes` model — same deferral as in `operations_module.md`.

## When to build this

Not now. Phases 1–3 of the operations module migration land first (workunit, dataset, update_custom_attributes). This is phase 4. The trigger to start is when either:

1. btools migrates into bfabricPy proper (the `register_custom_analysis.py` and `register_sushi_dataset_into_bfabric.py` scripts move in), or
2. `bfabric_app_runner.output_registration` is the next thing being touched and consolidation pays for itself, or
3. A third consumer appears and we've now got three implementations of the same orchestration.
