# `bfabric.operations` — First-Draft Implementation Plan

> **Scope:** this document is the migration plan from today's state (`bfabric.experimental` + `bfabric_rest_proxy.feeder_operations`) to the steady-state design described in `bfabric/docs/design/operations_module.md`. It is meant to be deleted once the migration is done.

## Goal of the first draft

Land the operations module with enough content to (a) demonstrate the shape works, (b) absorb every existing write capability currently scattered across `bfabric.experimental` and `bfabric_rest_proxy.feeder_operations`, and (c) leave deprecation shims in place so external consumers keep working through one release.

Non-goals for v1: new operations beyond what already exists today, a saga primitive, a typed `AuditAttributes` model, conflict-policy support, idempotent retry support. These live in "Future possibilities" in the design doc.

## Phasing

Three PRs, each independently mergeable. Order matters only between phase 2 and phase 1 (workunit migration touches the REST proxy; do it first so dataset isn't blocked by proxy review).

### Phase 1 — Skeleton + workunit migration

- Create `bfabric/operations/__init__.py` (empty re-exports for now).
- Create `bfabric/operations/workunit.py` with `CreateWorkunitParams` and `create_workunit(client, params, audit_attributes)`.
- Move private step helpers (`_create_workunit_initial`, `_resources`, `_parameters`, `_links`, `_complete_workunit`) from `bfabric_rest_proxy/feeder_operations/create_workunit.py` into the new module. Adjust `_create_workunit_initial` to write `audit_attributes` verbatim instead of hardcoded `"WebApp User"`.
- Add the failure-cleanup `try`/`except BaseException` (this is new behavior — current code has no cleanup).
- Replace the body of `bfabric_rest_proxy/feeder_operations/create_workunit.py` with a thin wrapper that does the `_check_container_access` authorization check, then calls `bfabric.operations.workunit.create_workunit` with `audit_attributes={"Generated Using": "bfabric-rest-proxy", "Generated For": user_client.auth.login}`.
- Tests:
  - Unit tests for `create_workunit` with a mocked `Bfabric` client, covering: happy path, failure at each compound step (verify cleanup runs), `audit_attributes` round-trip into the workunit custom-attributes call.
  - Existing REST proxy tests must continue to pass.

### Phase 2 — Dataset sub-package

- Create `bfabric/operations/dataset/` with `__init__.py`, `operations.py`, `transforms.py`, `validation.py`, `changes.py`, and `_column_types.py` (+ private `_column_types.yml` data file).
- Move:
  - `bfabric.experimental.upload_dataset.polars_to_bfabric_dataset` → `dataset.transforms.polars_to_dataset_dict` (rename).
  - `bfabric.experimental.upload_dataset.polars_column_to_bfabric_type` → private in `dataset.transforms`.
  - `bfabric.experimental.upload_dataset.check_for_invalid_characters` → `dataset.validation`.
  - `bfabric.experimental.upload_dataset.warn_on_trailing_spaces` → `dataset.validation`.
  - `bfabric.experimental.dataset_column_types` (.py + .yml) → private `dataset._column_types`.
  - From the `update-dataset` branch: `bfabric.experimental.dataset_changes` → `dataset.changes`.
- Add `create_dataset`, `update_dataset`, `preview_dataset_update`, and the `DatasetUpdatePreview` result model in `operations.py`.
- Replace `bfabric_save_csv2dataset` callers in the CLI with the composed form (`pl.read_csv` → `check_for_invalid_characters` → `create_dataset`). The old function is removed; the CLI shrinks.
- Tests:
  - Unit tests for `create_dataset`, `update_dataset`, `preview_dataset_update` with a mocked client.
  - Tests for `polars_to_dataset_dict` covering integer/string/entity-name columns.
  - CLI tests for the new composed-form `bfabric_save_csv2dataset` entry point (smoke level — the heavy lifting is unit-tested above).

### Phase 3 — Cross-entity primitive

- Move `bfabric.experimental.update_custom_attributes` → `bfabric/operations/update_custom_attributes.py`. Body unchanged.
- Re-export from `bfabric.operations.__init__` so the public import is `from bfabric.operations import update_custom_attributes`.
- Tests: keep existing tests; update imports.

## Migration table

| File | Fate | Notes |
| --- | --- | --- |
| `experimental/upload_dataset.py` | **Moved** → `bfabric.operations.dataset` (split across `transforms.py`, `validation.py`, `operations.py`) | `polars_to_bfabric_dataset` → `polars_to_dataset_dict` |
| `experimental/dataset_changes.py` (on `update-dataset` branch) | **Moved** → `bfabric.operations.dataset.changes` | Lands together with phase 2 |
| `experimental/update_custom_attributes.py` | **Moved** → `bfabric.operations.update_custom_attributes` (re-exported from `bfabric.operations.__init__`) | Phase 3 |
| `experimental/dataset_column_types.py` + `dataset_column_types.yml` | **Moved** → private inside `bfabric.operations.dataset._column_types` | Private location stops external imports from calcifying |
| `bfabric_rest_proxy/feeder_operations/create_workunit.py` | **Reduced** to thin authorization + composition wrapper | Phase 1 |
| `experimental/multi_query.py` | **Stays** | Not a write capability |
| `experimental/cache/` | **Stays** | Read-side caching |
| `experimental/webapp_integration_settings.py` | **Stays** | Not a write capability |
| `experimental/workunit_definition.py` | **Stays** | Read-side metadata helper |

After all three phases, `bfabric.experimental` contains the four "Stays" items plus the four deprecation shims. The package is not retired — it remains the staging area for future read-side or not-yet-stable code.

## Deprecation shim policy

For every "Moved" entry, the old module gets a module-level `__getattr__` that:

1. Imports the symbol from the new location.
2. Emits `DeprecationWarning` with a message naming the new import path.
3. Returns the symbol.

Shims live for **one release**, then are removed in the following release. The deprecation note goes in the changelog of the release that introduces the shim.

Concrete example for `bfabric.experimental.upload_dataset`:

```python
# bfabric/experimental/upload_dataset.py
import warnings

_NEW_LOCATIONS = {
    "polars_to_bfabric_dataset": (
        "bfabric.operations.dataset",
        "polars_to_dataset_dict",
    ),
    "check_for_invalid_characters": (
        "bfabric.operations.dataset",
        "check_for_invalid_characters",
    ),
    "warn_on_trailing_spaces": (
        "bfabric.operations.dataset",
        "warn_on_trailing_spaces",
    ),
}


def __getattr__(name: str):
    if name in _NEW_LOCATIONS:
        module_path, new_name = _NEW_LOCATIONS[name]
        warnings.warn(
            f"bfabric.experimental.upload_dataset.{name} moved to {module_path}.{new_name}; "
            "update imports — this shim will be removed in the next release.",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib

        return getattr(importlib.import_module(module_path), new_name)
    raise AttributeError(
        f"module 'bfabric.experimental.upload_dataset' has no attribute {name!r}"
    )
```

`bfabric_save_csv2dataset` is **not** in the shim table — it has no direct replacement (decomposed into CLI-level composition). The shim raises `AttributeError` with a message pointing to the composed form.

## Tests

- Unit tests live at `tests/bfabric/operations/<entity>/test_<verb>_<entity>.py`, mirroring the source layout. Tests must not have `__init__.py` (existing repo convention).
- Mocked `Bfabric` client for all unit tests — no real SOAP traffic. The conftest already sets `BFABRICPY_CONFIG_ENV=__MOCK`.
- Integration tests for `create_workunit` end-to-end live in the integration-test repo (out of scope here), but a smoke fixture that round-trips a workunit through the real proxy should be added there once phase 1 lands.
- Deprecation shims get tests that import the old path and assert the `DeprecationWarning` fires.

## Pre-merge checklist

Per phase, before merging:

- [ ] `nox -s test_bfabric` and `nox -s test_bfabric_scripts` green (and `nox -s test_bfabric_rest_proxy` for phase 1).
- [ ] `nox -s basedpyright(bfabric)` clean — no new baseline entries.
- [ ] `nox -s code_style` clean.
- [ ] Deprecation shim emits warning when imported via old path (covered by a test, not just manual check).
- [ ] Changelog entry naming the moved symbols and the deprecation timeline.
- [ ] One-line note in `bfabric/docs/changelog.md` (or wherever release notes live).

## Open implementation questions

These need a decision before or during coding, not at the design level:

- **Entity construction in operations.** Today's `_complete_workunit` uses `instantiate_entity(...)` with an `isinstance` guard; the design doc's dataset example uses direct `Dataset(result[0], client=..., bfabric_instance=...)`. Pick one and use it uniformly across operations. My recommendation: direct construction in operations, since the operation knows the type — `instantiate_entity`'s polymorphism doesn't earn its keep here. Decide before phase 1 lands.
- **Where does `Attribution` go if/when it becomes a typed model later?** Deferred to "Future possibilities", but if phase 3 (or a phase 4 not yet planned) makes audit attributes recur across operations, revisit whether `bfabric.operations.attribution` should exist. Not a phase-1 concern.
- **`DatasetUpdatePreview` with `arbitrary_types_allowed=True`** — using a Pydantic model that contains a `Dataset` (which is itself not a Pydantic model) needs this config. Confirm during phase 2 that this doesn't break serialization use-cases anywhere downstream. If it does, drop to a plain dataclass.
