# `bfabric.operations` Module Design

## Goals

Provide a stable home for **named write capabilities against B-Fabric**, organized by domain. Today these capabilities are spread across `bfabric.experimental` and `bfabric_rest_proxy.feeder_operations`. Consolidating them gives bfabricPy a single, supported surface for non-trivial writes and the helpers they need (transforms, validators, diffing).

The module exists so that consumers (REST proxy, landing apps, CLIs) can compose writes without each reimplementing them.

## Inclusion criterion

A piece of code belongs in `bfabric.operations.<domain>` when it is:

- **A write capability** for a B-Fabric entity (`create_dataset`, `update_dataset`, `create_workunit`), or a **pure helper** that exists primarily to support such capabilities (DataFrame ↔ SOAP transforms, dataset diffing, validation of write-bound inputs).
- **Deployment-agnostic** — it makes no assumption about whose credentials it runs under, what authorization happened beforehand, or what UI surrounds it.

Out of scope: single-SOAP-call writes that need no transform or coordination (callers use `client.save(...)` directly), authorization assertions, prompting/UI logic, and entity-read helpers (those live on the read-only entities).

## Layout per domain

**A domain is named after the B-Fabric entity it writes to** (`workunit`, `dataset`, `sample`, ...). Each domain is either a **single file** or a **sub-package**, chosen by what the domain actually contains:

- **Single file** (`<entity>.py`) when the domain has a small number of capabilities, even if each is internally compound. Example: `workunit.py` — currently one function, `create_workunit`, with private step helpers.
- **Sub-package** (`<entity>/`) when the domain has enough capabilities and shared machinery that one file becomes awkward. Example: `dataset/` — multiple operations plus shared pure helpers (transforms, validators, diffing).

Sub-package is a "this file outgrew comfort" decision, not a different category. A `workunit/` sub-package would emerge later if `update_workunit`, `cancel_workunit`, etc. accumulate and shared helpers appear; until then, `workunit.py` is the right shape.

```
bfabric/operations/
  __init__.py
  workunit.py                 # single-file domain
  dataset/                    # sub-package domain
    __init__.py
    operations.py
    transforms.py
    validation.py
    changes.py
```

The public import path is always `from bfabric.operations.<entity> import <verb>_<entity>` — uniform whether the domain is a file or a sub-package.

### Cross-entity primitives

A write capability that operates on *any* entity — typically via `EntityUri` or `(entity_type, entity_id)` — does not fit under a single entity-named module. Examples: `update_custom_attributes` (currently in `bfabric.experimental`), which merges custom attributes on an entity identified by URI.

These live at the **top level** of `bfabric.operations` and are re-exported from `bfabric.operations.__init__`, so the import path is `from bfabric.operations import update_custom_attributes`. The implementation file (`bfabric/operations/update_custom_attributes.py`) is an implementation detail. The convention is that an entity-named module is preferred when the capability is meaningfully bound to one entity type; the top-level position is reserved for genuinely cross-entity primitives.

## Shared conventions (universal)

What every domain must follow:

- **Pydantic input models** for parameter sets (`CreateWorkunitParams`, `CreateDatasetParams`).
- **Read-only entity outputs.** The write returns a populated entity from `bfabric.entities`. Entities stay read-only.
- **Per-operation failure cleanup** for any capability that can leave partial state — see the canonical pattern below.
- **The public surface is the domain-level import path**: `from bfabric.operations.dataset import create_dataset` and `from bfabric.operations.workunit import create_workunit`. Sub-package `__init__.py` re-exports.
- **Audit identity is caller-supplied data, not a hardcoded schema.** Operations that stamp audit information on created entities take an `audit_attributes: dict[str, str]` parameter and write it verbatim. The operations module has no opinion about what audit attribute names a deployment uses (see workunit example).

### Failure cleanup pattern

Compound operations that leave partial state on error must mark that state as `failed` (or equivalent) so it is not mistaken for in-progress work. The canonical shape:

```python
created_id = _initial_create_step(client, ...)
try:
    # ... remaining steps ...
    return _complete(client, created_id)
except BaseException:
    try:
        client.save(entity, {"id": created_id, "status": "failed"})
    except BaseException as e:
        logger.error(f"Cleanup failed for {entity} {created_id}: {e!r}")
    raise
```

Three things that make this pattern correct, all of them load-bearing:

- **Outer `except BaseException`** so `KeyboardInterrupt` and `SystemExit` also trigger cleanup. Ordinary `except Exception` would skip them and leave orphans.
- **Inner `try`/`except BaseException` that logs and does not re-raise**, so a cleanup failure cannot mask the original error. The outer `raise` re-raises the original.
- **No attempt to delete already-created child entities** (resources, parameters, links). Those stay attached to the failed parent so the partial state is diagnosable. Aggressive cleanup is a separate decision; do not invent it ad-hoc.

Copy this shape verbatim for new compound operations; do not invent variants.

## Per-domain variation (allowed)

What each domain decides for itself:

- Single-file vs. sub-package.
- Whether to expose pure transforms, validators, or diff helpers (some domains have them, others don't).
- Whether to take an `audit_attributes` parameter (only delegated writes need one; see workunit example).
- Internal organization within the sub-package.
- **Whether the payload is bundled into the params model or passed separately.** Dataset operations take the Polars DataFrame as a separate positional argument and the metadata as a pydantic params model; workunit bundles everything into the params model. The split is deliberate: the DataFrame is a large payload validated by polars, while the dataset metadata is small and validated by pydantic — keeping them apart avoids round-tripping a DataFrame through pydantic and lets previews/dry-runs share the same params model without re-parsing the data. Workunit has no comparable payload — every input is small metadata — so a single params model is the cleaner shape there.

## Worked example 1 — workunit (single-capability domain)

`create_workunit` is one compound write capability. It performs multiple coordinated SOAP calls, needs failure cleanup, and is delegated (audit-stamped). One file, one public function, private step helpers.

```python
# bfabric/operations/workunit.py
from __future__ import annotations

from loguru import logger
from pydantic import BaseModel, Field, model_validator

from bfabric import Bfabric
from bfabric.entities import Workunit


class CreateWorkunitParams(BaseModel):
    container_id: int
    application_id: int
    workunit_name: str
    parameters: dict[str, str] = Field(default_factory=dict, max_length=100)
    resources: dict[str, str] = Field(default_factory=dict, max_length=100)
    links: dict[str, str] = Field(default_factory=dict, max_length=100)
    input_resource_ids: list[int] = Field(default_factory=list, max_length=100)
    description: str = ""

    @model_validator(mode="after")
    def _ensure_data(self) -> "CreateWorkunitParams":
        if not self.parameters and not self.resources and not self.links:
            raise ValueError(
                "No workunit data provided; specify parameters, resources, or links"
            )
        return self


def create_workunit(
    client: Bfabric,
    params: CreateWorkunitParams,
    audit_attributes: dict[str, str] | None = None,
) -> Workunit:
    """Create a workunit with its resources, parameters, and links.

    `audit_attributes` is written verbatim as workunit custom attributes; the
    operation has no opinion about what keys are used. On failure at any step
    after the initial workunit creation, the workunit is flipped to status
    "failed" (see Failure cleanup pattern).
    """
    workunit_id = _create_workunit_initial(client, params, audit_attributes or {})
    try:
        if params.resources:
            _create_workunit_resources(client, workunit_id, params.resources)
        if params.parameters:
            _create_workunit_parameters(client, workunit_id, params.parameters)
        if params.links:
            _create_workunit_links(client, workunit_id, params.links)
        return _complete_workunit(client, workunit_id)
    except BaseException:
        try:
            client.save("workunit", {"id": workunit_id, "status": "failed"})
        except BaseException as e:
            logger.error(
                f"Failed to mark workunit {workunit_id} failed during cleanup: {e!r}"
            )
        raise


# _create_workunit_initial / _resources / _parameters / _links / _complete_workunit:
# private step helpers, structurally unchanged from the current rest-proxy implementation
# except that _create_workunit_initial writes `audit_attributes` as workunit
# customattributes (replacing the hardcoded "WebApp User" stamp).
```

### Consumer composition

The REST proxy keeps its endpoint contract by composing an authorization check with the operation. Authorization stays in the proxy because it depends on the proxy's auth model. Picking the audit-attribute schema also stays in the proxy.

```python
# bfabric_rest_proxy/feeder_operations/create_workunit.py
def create_workunit_for_webapp_user(user_client, feeder_client, params):
    _check_container_access(user_client, params.container_id)
    return bfabric.operations.workunit.create_workunit(
        client=feeder_client,
        params=params,
        audit_attributes={
            "Generated Using": "bfabric-rest-proxy",
            "Generated For": user_client.auth.login,
        },
    )
```

The proxy can keep stamping `"WebApp User"` instead, or both keys, during a transition — that decision sits with the proxy, not with `bfabric.operations`.

## Worked example 2 — dataset (multi-capability domain)

Datasets have multiple write capabilities (create, update, preview-update) that share machinery (DataFrame transforms, validators, diff). Sub-package with each concern in its own module. Public API re-exported from `__init__.py`.

### Layout

```
bfabric/operations/dataset/
  __init__.py
  operations.py       # create_dataset, update_dataset, preview_dataset_update
  transforms.py       # polars_to_dataset_dict + type inference
  validation.py       # check_for_invalid_characters, warn_on_trailing_spaces
  changes.py          # DatasetChanges, identify_changes
```

### `__init__.py` — public surface

```python
# bfabric/operations/dataset/__init__.py
from bfabric.operations.dataset.changes import DatasetChanges, identify_changes
from bfabric.operations.dataset.operations import (
    CreateDatasetParams,
    DatasetUpdatePreview,
    create_dataset,
    preview_dataset_update,
    update_dataset,
)
from bfabric.operations.dataset.transforms import polars_to_dataset_dict
from bfabric.operations.dataset.validation import (
    check_for_invalid_characters,
    warn_on_trailing_spaces,
)
```

### `operations.py` — the write capabilities

```python
# bfabric/operations/dataset/operations.py
from __future__ import annotations

import polars as pl
from pydantic import BaseModel

from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric.operations.dataset.changes import DatasetChanges, identify_changes
from bfabric.operations.dataset.transforms import polars_to_dataset_dict


class CreateDatasetParams(BaseModel):
    name: str
    container_id: int
    workunit_id: int | None = None


class DatasetUpdatePreview(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    current: Dataset
    changes: DatasetChanges


def create_dataset(
    client: Bfabric,
    table: pl.DataFrame,
    params: CreateDatasetParams,
) -> Dataset:
    """Create a new B-Fabric dataset from a Polars DataFrame.

    Validation (forbidden characters, trailing whitespace) is the caller's
    responsibility — apply `check_for_invalid_characters` / `warn_on_trailing_spaces`
    beforehand if needed. This is a deliberate split: previews, dry-runs, and
    tests want to skip validation, and interactive callers want to surface
    validation errors before the network call. See "Validation is caller-side"
    note below.
    """
    obj = polars_to_dataset_dict(table)
    obj["name"] = params.name
    obj["containerid"] = params.container_id
    if params.workunit_id is not None:
        obj["workunitid"] = params.workunit_id
    result = client.save("dataset", obj)
    return Dataset(result[0], client=client, bfabric_instance=client.config.base_url)


def update_dataset(client: Bfabric, dataset_id: int, table: pl.DataFrame) -> Dataset:
    """Replace the content of an existing dataset with `table`.

    Does not diff or confirm. For interactive flows, call `preview_dataset_update` first.
    """
    obj = polars_to_dataset_dict(table)
    obj["id"] = dataset_id
    result = client.save("dataset", obj)
    return Dataset(result[0], client=client, bfabric_instance=client.config.base_url)


def preview_dataset_update(
    client: Bfabric,
    dataset_id: int,
    new_table: pl.DataFrame,
) -> DatasetUpdatePreview:
    """Read the existing dataset and report what would change if updated to `new_table`.

    Does not write. Intended for interactive flows that want to confirm before
    calling `update_dataset`.
    """
    existing = client.reader.read_id("dataset", dataset_id, expected_type=Dataset)
    if existing is None:
        raise RuntimeError(f"Dataset {dataset_id} not found")
    changes = identify_changes(old_df=existing.to_polars(), new_df=new_table)
    return DatasetUpdatePreview(current=existing, changes=changes)
```

#### Validation is caller-side (note)

`bfabric_save_csv2dataset` today calls `check_for_invalid_characters` inside the save function. Pushing validation to the caller is a deliberate trade-off:

- **Gained:** composable previews and dry-runs (skip validation), test fixtures without character-class noise, and a single source of truth when a caller wants stricter or looser rules than the library default.
- **Lost:** every caller must remember to call `check_for_invalid_characters` first. In practice the CLI and proxy each call it exactly once, so the burden is small — but it must be enforced in code review, not by the function signature.

If this turns out to be error-prone in practice, the fix is to add a thin wrapper (`create_dataset_validated`) rather than re-bundling validation into the primitive.

### `transforms.py`, `validation.py`, `changes.py`

These are pure helpers organized by concern:

- **`transforms`** — `polars_to_dataset_dict` and a private `polars_column_to_bfabric_type` for inferring B-Fabric column types from a Polars DataFrame.
- **`validation`** — `check_for_invalid_characters` (raises) and `warn_on_trailing_spaces` (logs). Caller-side; see note above.
- **`changes`** — `DatasetChanges` model and `identify_changes(old_df, new_df)` for previews.

### Why this shape for dataset and not workunit

- Datasets have **pure helpers worth publishing** (`polars_to_dataset_dict` is reusable for previews, dry-runs, tests; `identify_changes` is useful even outside the write flow). Workunit has nothing comparable — every step is bound to the SOAP boundary.
- Datasets have **multiple distinct capabilities** (create, update, preview). Workunit has one.
- Datasets have **no compound-state failure mode** at the operation level — both `create_dataset` and `update_dataset` are single SOAP calls. Workunit needs explicit cleanup.

The asymmetry is what the domain looks like, not inconsistency in the module design.

## Decisions deferred to consumers (not the operations module)

Three things that look like operations-module concerns but are deliberately not. Recording them here so a future maintainer doesn't accidentally pull them in.

- **Audit attribute schema.** What keys (`"WebApp User"`, `"Generated Using"`, …) end up on a created workunit is a deployment decision. Operations take a `dict[str, str]` and stamp it.
- **Idempotency / retry safety.** `create_workunit` retried after a transient error creates a duplicate. Detection and dedup are not in scope for v1; if a consumer needs them, it adds a wrapper that searches first. Building idempotency into operations would require a stable client-side key, which B-Fabric does not currently expose.
- **Orphan child cleanup on workunit failure.** Resources/parameters/links attached to a workunit that subsequently fails stay attached. The failed-status mark is enough — the partial state remains visible for diagnosis. If a consumer wants stricter cleanup (e.g. for a sandbox container), it does so itself.

## Open question

**OAuth scoping and authorization.** An OAuth extension is on the roadmap. Today the REST proxy's authorization check is a SOAP read against the target entity using the user's credentials. Under OAuth, authorization may shift to token-scope inspection without a SOAP call.

This is expected to affect the proxy and consumers — not `bfabric.operations` itself, since operations carry `audit_attributes` (audit identity) rather than credentials (authorization). Verification when OAuth lands: do the worked-example signatures still hold without changes? Expected answer: yes. If not, the split between operations and authorize was wrong and the design needs revisiting.

## Future possibilities

Listed so future migrations remember they were considered, not committed:

- **More domains.** Charging, link creation, sample registration — each evaluated against the inclusion criterion when it comes up.
- **A shared saga primitive.** Only if a second compound write arrives that needs reverse-order compensation across multiple distinct steps. The current pattern (per-operation try/except, codified in "Failure cleanup pattern") handles workunit cleanly and is unnecessary for dataset.
- **A typed `AuditAttributes` model.** If the same audit-attribute keys are stamped by multiple operations and the dict-of-str shape starts looking ad-hoc, a small Pydantic model with named fields could replace `dict[str, str]` at the call site. Today, with one delegated write (`create_workunit`), the dict is simpler than a model. Revisit when a second delegated write appears.
- **Stateful write helpers (e.g. a Job logger that batches writes to `job.logthis`).** Don't fit the current inclusion criterion ("write capability"). If they arrive, the criterion either expands or such helpers get their own home (e.g. `bfabric.logging.job`).
- **A "conflict policy" parameter for compound operations.** `bfabric_app_runner` uses an `UpdateExisting` enum (`NO` / `IF_EXISTS` / `REQUIRED`) when registering resources and links to control find-or-create-or-fail behavior. It currently lives in `bfabric_app_runner.specs.outputs_spec` and is app-runner policy. If the same shape appears outside app_runner — e.g. another consumer needs operations to take "what to do if it already exists" as a caller-supplied parameter — the enum (or an equivalent vocabulary) may move to `bfabric.operations` so multiple consumers can share it. Today this is app-runner-internal and stays there.
