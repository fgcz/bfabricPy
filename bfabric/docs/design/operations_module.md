# `bfabric.operations` Module Design

## Purpose

`bfabric.operations` is the home for **named write capabilities against B-Fabric**, organized by domain. It gives bfabricPy a single, supported surface for non-trivial writes and the helpers they need (transforms, validators, diffing), so that consumers (REST proxy, landing apps, CLIs) can compose writes without each reimplementing them.

## Inclusion criterion

A piece of code belongs in `bfabric.operations.<domain>` when it is:

- **A write capability** for a B-Fabric entity (`create_dataset`, `update_dataset`, `create_workunit`), or a **pure helper** that exists primarily to support such capabilities (DataFrame ↔ SOAP transforms, dataset diffing, validation of write-bound inputs).
- **Deployment-agnostic** — it makes no assumption about whose credentials it runs under, what authorization happened beforehand, or what UI surrounds it.

Out of scope: single-SOAP-call writes that need no transform or coordination (callers use `client.save(...)` directly), authorization assertions, prompting/UI logic, and entity-read helpers (those live on the read-only entities).

## Layout per domain

**A domain is named after the B-Fabric entity it writes to** (`workunit`, `dataset`, `sample`, ...). Each domain is either a **single file** or a **sub-package**, chosen by what the domain actually contains:

- **Single file** (`<entity>.py`) when the domain has a small number of capabilities, even if each is internally compound. Example: `workunit.py` — one function, `create_workunit`, with private step helpers.
- **Sub-package** (`<entity>/`) when the domain has enough capabilities and shared machinery that one file becomes awkward. Example: `dataset/` — multiple operations plus shared pure helpers (transforms, validators, diffing).

Sub-package is a "this file outgrew comfort" decision, not a different category. A `workunit/` sub-package would emerge later if `update_workunit`, `cancel_workunit`, etc. accumulate and shared helpers appear; until then, `workunit.py` is the right shape.

The public import path is always `from bfabric.operations.<entity> import <verb>_<entity>` — uniform whether the domain is a file or a sub-package.

### Cross-entity primitives

A write capability that operates on *any* entity — typically via `EntityUri` or `(entity_type, entity_id)` — does not fit under a single entity-named module. Example: `update_custom_attributes`, which merges custom attributes on an entity identified by URI.

These live at the **top level** of `bfabric.operations` and are re-exported from `bfabric.operations.__init__`, so the import path is `from bfabric.operations import update_custom_attributes`. The convention is that an entity-named module is preferred when the capability is meaningfully bound to one entity type; the top-level position is reserved for genuinely cross-entity primitives.

## Shared conventions (universal)

What every domain must follow:

- **Pydantic input models** for parameter sets (`CreateWorkunitParams`, `CreateDatasetParams`).
- **Read-only entity outputs.** The write returns a populated entity from `bfabric.entities`. Entities stay read-only.
- **Per-operation failure cleanup** for any capability that can leave partial state — see the canonical pattern below.
- **The public surface is the domain-level import path**: `from bfabric.operations.dataset import create_dataset` and `from bfabric.operations.workunit import create_workunit`. Sub-package `__init__.py` re-exports.
- **Audit identity is caller-supplied data, not a hardcoded schema.** Operations that stamp audit information on created entities take an `audit_attributes: dict[str, str]` parameter and write it verbatim. The operations module has no opinion about what audit attribute names a deployment uses.

### Failure cleanup pattern

Compound operations that leave partial state on error must mark that state as `failed` (or equivalent) so it is not mistaken for in-progress work. The canonical shape (see `workunit.create_workunit` for the reference implementation):

1. Perform the initial create step and remember the new entity id.
2. Wrap the remaining steps in a `try` block, returning the completed entity on success.
3. Catch **`BaseException`** (not `Exception`) so `KeyboardInterrupt` and `SystemExit` also trigger cleanup, then `save` the entity with `status="failed"`.
4. The cleanup `save` itself is wrapped in an inner `try` / `except BaseException` that logs and does not re-raise, so a cleanup failure cannot mask the original error.
5. Do **not** attempt to delete already-created child entities (resources, parameters, links). They stay attached to the failed parent so the partial state is diagnosable. Aggressive cleanup is a separate decision; do not invent it ad-hoc.

Copy this shape verbatim for new compound operations; do not invent variants.

## Per-domain variation (allowed)

What each domain decides for itself:

- Single-file vs. sub-package.
- Whether to expose pure transforms, validators, or diff helpers (some domains have them, others don't).
- Whether to take an `audit_attributes` parameter (only delegated writes need one).
- Internal organization within the sub-package.
- **Whether the payload is bundled into the params model or passed separately.** Dataset operations take the Polars DataFrame as a separate positional argument and the metadata as a pydantic params model; workunit bundles everything into the params model. The split is deliberate: the DataFrame is a large payload validated by polars, while the dataset metadata is small and validated by pydantic — keeping them apart avoids round-tripping a DataFrame through pydantic and lets previews/dry-runs share the same params model without re-parsing the data. Workunit has no comparable payload — every input is small metadata — so a single params model is the cleaner shape there.

## Domain 1 — workunit (single-capability domain)

`create_workunit` is one compound write capability. It performs multiple coordinated SOAP calls (workunit + resources + parameters + links + completion), needs failure cleanup, and is delegated (audit-stamped). One file, one public function, private step helpers.

The operation takes a `CreateWorkunitParams` pydantic model and an `audit_attributes: dict[str, str]` that is written verbatim as workunit custom attributes. On failure at any step after the initial workunit creation, the workunit is flipped to status `"failed"` per the cleanup pattern above.

### Consumer composition

The REST proxy keeps its endpoint contract by composing an authorization check with the operation. Authorization stays in the proxy because it depends on the proxy's auth model. Picking the audit-attribute schema also stays in the proxy — it chooses the keys (e.g. `"Generated Using"`, `"Generated For"`) and passes them through. The proxy can keep stamping legacy keys, new keys, or both during a transition; that decision sits with the proxy, not with `bfabric.operations`.

## Domain 2 — dataset (multi-capability domain)

Datasets have multiple write capabilities (create, update, preview-update) that share machinery (DataFrame transforms, validators, diff). Sub-package with each concern in its own module. Public API re-exported from `__init__.py`:

- `operations.py` — `create_dataset`, `update_dataset`, `preview_dataset_update`, params/result models.
- `transforms.py` — `polars_to_dataset_dict` and B-Fabric column-type inference.
- `validation.py` — `check_for_invalid_characters` (raises) and `warn_on_trailing_spaces` (logs).
- `changes.py` — `DatasetChanges` model and `identify_changes(old_df, new_df)` for previews.

`create_dataset` and `update_dataset` are each a single SOAP call wrapping a DataFrame-to-dict transform. `preview_dataset_update` reads the existing dataset and reports what would change without writing — intended for interactive flows that want to confirm before calling `update_dataset`.

### Validation is caller-side

`check_for_invalid_characters` and `warn_on_trailing_spaces` are not invoked inside `create_dataset`/`update_dataset`. Callers apply them beforehand if needed. This is a deliberate trade-off:

- **Gained:** composable previews and dry-runs (skip validation), test fixtures without character-class noise, and a single source of truth when a caller wants stricter or looser rules than the library default.
- **Lost:** every caller must remember to call validators first. In practice the CLI and proxy each call them exactly once, so the burden is small — but it must be enforced in code review, not by the function signature.

If this turns out to be error-prone in practice, the fix is to add a thin wrapper (`create_dataset_validated`) rather than re-bundling validation into the primitive.

### Why this shape for dataset and not workunit

- Datasets have **pure helpers worth publishing** (`polars_to_dataset_dict` is reusable for previews, dry-runs, tests; `identify_changes` is useful even outside the write flow). Workunit has nothing comparable — every step is bound to the SOAP boundary.
- Datasets have **multiple distinct capabilities** (create, update, preview). Workunit has one.
- Datasets have **no compound-state failure mode** at the operation level — both `create_dataset` and `update_dataset` are single SOAP calls. Workunit needs explicit cleanup.

The asymmetry is what the domain looks like, not inconsistency in the module design.

## Decisions deferred to consumers (not the operations module)

Three things that look like operations-module concerns but are deliberately not. Recording them here so a future maintainer doesn't accidentally pull them in.

- **Audit attribute schema.** What keys (`"WebApp User"`, `"Generated Using"`, …) end up on a created workunit is a deployment decision. Operations take a `dict[str, str]` and stamp it.
- **Idempotency / retry safety.** `create_workunit` retried after a transient error creates a duplicate. Detection and dedup are not in scope; if a consumer needs them, it adds a wrapper that searches first. Building idempotency into operations would require a stable client-side key, which B-Fabric does not currently expose.
- **Orphan child cleanup on workunit failure.** Resources/parameters/links attached to a workunit that subsequently fails stay attached. The failed-status mark is enough — the partial state remains visible for diagnosis. If a consumer wants stricter cleanup (e.g. for a sandbox container), it does so itself.

## Open question

**OAuth scoping and authorization.** An OAuth extension is on the roadmap. Today the REST proxy's authorization check is a SOAP read against the target entity using the user's credentials. Under OAuth, authorization may shift to token-scope inspection without a SOAP call.

This is expected to affect the proxy and consumers — not `bfabric.operations` itself, since operations carry `audit_attributes` (audit identity) rather than credentials (authorization). Verification when OAuth lands: do the operation signatures still hold without changes? Expected answer: yes. If not, the split between operations and authorize was wrong and the design needs revisiting.

## Future possibilities

Listed so future migrations remember they were considered, not committed:

- **More domains.** Charging, link creation, sample registration — each evaluated against the inclusion criterion when it comes up.
- **A shared saga primitive.** Only if a second compound write arrives that needs reverse-order compensation across multiple distinct steps. The current pattern (per-operation try/except, codified in "Failure cleanup pattern") handles workunit cleanly and is unnecessary for dataset.
- **A typed `AuditAttributes` model.** If the same audit-attribute keys are stamped by multiple operations and the dict-of-str shape starts looking ad-hoc, a small Pydantic model with named fields could replace `dict[str, str]` at the call site. Today, with one delegated write (`create_workunit`), the dict is simpler than a model. Revisit when a second delegated write appears.
- **Stateful write helpers (e.g. a Job logger that batches writes to `job.logthis`).** Don't fit the current inclusion criterion ("write capability"). If they arrive, the criterion either expands or such helpers get their own home (e.g. `bfabric.logging.job`).
- **A "conflict policy" parameter for compound operations.** `bfabric_app_runner` uses an `UpdateExisting` enum (`NO` / `IF_EXISTS` / `REQUIRED`) when registering resources and links to control find-or-create-or-fail behavior. It currently lives in `bfabric_app_runner.specs.outputs_spec` and is app-runner policy. If the same shape appears outside app_runner, the enum (or an equivalent vocabulary) may move to `bfabric.operations` so multiple consumers can share it. Today this is app-runner-internal and stays there.
