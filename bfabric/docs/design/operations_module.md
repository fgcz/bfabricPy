# `bfabric.operations` Module Design

## Purpose and scope

`bfabric.operations` is the home for **named write capabilities against B-Fabric**, organized by domain. It gives bfabricPy a single, supported surface for non-trivial writes and the helpers they need (transforms, validators, diffing), so consumers (REST proxy, landing apps, CLIs) compose writes without each reimplementing them.

Code belongs here when it is a write capability for a B-Fabric entity, or a pure helper that exists primarily to support such capabilities (DataFrame ↔ SOAP transforms, diffing, validation of write-bound inputs) — *and* it is deployment-agnostic, making no assumption about whose credentials it runs under, what authorization happened beforehand, or what UI surrounds it. Single-SOAP-call writes that need no transform or coordination do not belong here; callers use `client.save(...)` directly. Authorization assertions, prompting/UI logic, and entity-read helpers also stay out — read helpers live on the read-only entities.

## Module layout

**A domain is named after the B-Fabric entity it writes to** (`workunit`, `dataset`, `sample`, ...) and is implemented as either a single file (`<entity>.py`) or a sub-package (`<entity>/`). The choice is purely about readability: start as a file, promote to a sub-package when shared machinery accumulates. Either way the public import path is `from bfabric.operations.<entity> import <verb>_<entity>` — sub-package `__init__.py` re-exports so callers never see the internal split.

A few write capabilities operate on *any* entity, typically via `EntityUri` or `(entity_type, entity_id)`, and don't fit under a single entity-named module — `update_custom_attributes` is the current example. These live at the top level of `bfabric.operations` and are re-exported from `bfabric.operations.__init__`, so the import path is `from bfabric.operations import update_custom_attributes`. The top level is reserved for *genuinely* cross-entity primitives; anything meaningfully bound to one entity type goes under its entity module.

## The operation contract

Every operation, regardless of domain, follows a small fixed contract:

- **Inputs** are validated by a pydantic params model. Where an operation also takes a large payload that pydantic doesn't validate well (e.g. a Polars DataFrame), the payload is a separate positional argument and the params model stays metadata-only.
- **Outputs** are populated read-only entities from `bfabric.entities`. Operations never invent their own return types and entities never gain write methods.
- **Audit identity** is supplied by the caller as `audit_attributes: dict[str, str]` and written verbatim onto the created entity. The operations module has no opinion about which keys a deployment uses; only delegated writes need this parameter at all.

**Compound operations need failure cleanup.** Any capability that can leave partial state on error must mark that state as `failed` (or equivalent) so it is not mistaken for in-progress work. The canonical shape: perform the initial create step and remember the new entity id; wrap the remaining steps in a `try` returning the completed entity on success; on **`BaseException`** (not `Exception` — `KeyboardInterrupt` and `SystemExit` must also trigger cleanup) `save` the entity with `status="failed"`, wrapping that cleanup `save` in an inner `try` / `except BaseException` that logs and does not re-raise so a cleanup failure cannot mask the original error. Do not delete already-created child entities (resources, parameters, links): they stay attached to the failed parent so the partial state is diagnosable. Copy this shape verbatim for new compound operations; do not invent variants.

Within those rules each domain has latitude over its internal organization, which pure helpers (transforms, validators, diff) it exposes, and whether validators run inside the operation or are left for callers to apply. Caller-side validation enables previews, dry-runs, and test fixtures to skip it, at the cost of every caller remembering to invoke validators first. If that becomes error-prone in practice, the fix is a thin `<verb>_<entity>_validated` wrapper, not rebundling validation into the primitive.

## What the contract leaves to the caller

Several things look like operations-module concerns but are deliberately left to consumers, recorded here so a future maintainer doesn't pull them in.

**Authorization** stays in each consumer — every consumer applies its own check before invoking an operation, and the operations module assumes the caller has already decided the write is allowed. **Choosing audit attribute keys** is a deployment decision: operations stamp whatever `dict[str, str]` they're given. **Idempotency / retry safety** is also out of scope — retrying a compound create after a transient error may produce a duplicate, and a consumer that needs deduplication adds a wrapper that searches first; building idempotency in would require a stable client-side key that B-Fabric does not currently expose. **Orphan child cleanup** on failure is similarly the consumer's call: children attached to a failed parent stay attached and the failed-status mark is enough for diagnosis, but a consumer that wants stricter cleanup (e.g. a sandbox container) does it itself.

## Open questions and future work

**OAuth scoping and authorization.** An OAuth extension is on the roadmap. Today the REST proxy's authorization check is a SOAP read against the target entity using the user's credentials; under OAuth, authorization may shift to token-scope inspection without a SOAP call. This is expected to affect the proxy and other consumers — not `bfabric.operations` itself, since operations carry `audit_attributes` (audit identity) rather than credentials (authorization). The verification when OAuth lands is whether the operation signatures still hold without changes; the expected answer is yes, and if not the split between operations and authorize was wrong and the design needs revisiting.

A handful of extensions have been considered but not committed:

- **More domains** (charging, link creation, sample registration) — each evaluated against the inclusion criterion when it arrives.
- **A shared saga primitive** — only if a compound write arrives that needs reverse-order compensation across multiple distinct steps. The per-operation try/except pattern above is sufficient until then.
- **A typed `AuditAttributes` model** — if the same audit-attribute keys end up stamped by multiple operations and the dict-of-str shape starts looking ad-hoc, a small pydantic model could replace it. Revisit when a second delegated write appears.
- **Stateful write helpers** (e.g. a Job logger that batches writes to `job.logthis`) — don't fit the current inclusion criterion. If they arrive, either the criterion expands or they get their own home (e.g. `bfabric.logging.job`).
- **A "conflict policy" parameter for compound operations.** `bfabric_app_runner` uses an `UpdateExisting` enum (`NO` / `IF_EXISTS` / `REQUIRED`) when registering resources and links. If the same shape appears outside app_runner, the enum (or an equivalent vocabulary) may move here so consumers can share it. Today it stays in app_runner.
