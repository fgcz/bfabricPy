# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

bfabricPy is a Python client library for [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/), a data management platform at the Functional Genomics Center Zurich (FGCZ). It communicates with B-Fabric via SOAP/WSDL.

## Monorepo Structure

This is a **uv workspace** with 5 packages:

| Package | Purpose | Min Python |
|---------|---------|------------|
| `bfabric` | Core client library | 3.11 |
| `bfabric_scripts` | CLI scripts and utilities | 3.11 |
| `bfabric_app_runner` | Application runner for workflows | 3.12 |
| `bfabric_rest_proxy` | FastAPI REST proxy | 3.12 |
| `bfabric_asgi_auth` | ASGI auth middleware | 3.13 |

Each package has its own `pyproject.toml` under its directory. Workspace references mean changes to `bfabric` are immediately available to dependent packages.

## Common Commands

### Setup
```bash
uv sync --all-packages --all-extras
```

### Testing (nox — recommended)
```bash
nox                                    # all test sessions
nox -s test_bfabric                    # core package only
nox -s test_bfabric_scripts            # scripts package
nox -s test_bfabric_app_runner         # app runner
nox -s test_bfabric-3.13              # specific Python version
nox -s test_bfabric-3.11(lowest-direct) # specific resolution strategy
```

### Testing (pytest — direct, after uv sync)
```bash
pytest tests/bfabric                   # core package
pytest tests/bfabric_scripts           # scripts (also tests/bfabric_cli)
pytest tests/bfabric_app_runner        # app runner
pytest tests/bfabric/test_something.py # single file
pytest tests/bfabric -k test_name      # single test
```

Run each package's suite in a **separate** `pytest` invocation (as nox does). Passing
multiple package trees to one invocation (e.g. `pytest tests/bfabric tests/bfabric_app_runner`)
fails at collection with a basename clash, because tests have no `__init__.py` (see the
convention below) so identically-named modules across trees collide.

### Type Checking
```bash
nox -s basedpyright(bfabric)
nox -s basedpyright(bfabric_scripts)
nox -s basedpyright(bfabric_app_runner)
```

### Linting
```bash
nox -s code_style                      # ruff via nox
ruff check bfabric                     # ruff directly
```

### Docs
```bash
nox -s docs                            # build all docs to site/
cd bfabric/docs && make html           # local preview
```

## Architecture

### Core Client (`bfabric/src/bfabric/`)

- **`bfabric.py`** — `Bfabric` class: the main client. Create via `Bfabric.connect()` (config file) or `Bfabric.connect_webapp()` (token auth). Provides `read()`, `save()`, `delete()`, `exists()`, `upload_resource()`.
- **`config/`** — Pydantic-based config: `BfabricAuth` (login + 32-char SecretStr password), `BfabricClientConfig` (base_url, engine choice), loaded from `~/.bfabricpy.yml`. Environment selection via `BFABRICPY_CONFIG_ENV`. Override via `BFABRICPY_CONFIG_OVERRIDE` (JSON).
- **`engine/`** — Strategy pattern for SOAP transport: `EngineSUDS` (default, suds library) and `EngineZeep` (optional zeep library, install via `bfabric[zeep]`). Both implement the same read/save/delete interface.
- **`entities/`** — Entity models with `HasOne`/`HasMany` relationship descriptors and lazy loading. `EntityReader` provides ORM-like access with caching (`cache_entities()` context manager).
- **`results/`** — `ResultContainer` wraps API responses with pagination, error handling, and `to_polars()` conversion.
- **`utils/cli_integration.py`** — `@use_client` decorator for CLI commands: auto-creates `Bfabric` client, injects config_env/config_file parameters.

### CLI (`bfabric_scripts/src/bfabric_scripts/cli/`)

Modern CLI built with **cyclopts**: `bfabric-cli api|dataset|executable|workunit|feeder|external-job`. Legacy scripts (`bfabric_read.py`, etc.) are preserved as entry points.

### App Runner (`bfabric_app_runner/`)

Handles dispatch → process → collect workflow for B-Fabric applications. Uses pydantic for spec validation, mako for templating.

## Documentation

Each package's docs live alongside its source. Skim the index when working in a package — it links to user guides, API reference, and changelog.

- `bfabric/docs/index.md` — core client (getting started, user guides, API reference, advanced topics, design)
- `bfabric_app_runner/docs/index.md` — app runner (getting started, user guides, API reference)
- `bfabric_scripts/docs/changelog.md` — scripts (changelog only; no full docs site)
- `bfabric_rest_proxy/README.md`, `bfabric_rest_proxy/docs/changelog.md` — REST proxy
- `bfabric_asgi_auth/README.md`, `bfabric_asgi_auth/docs/changelog.md` — ASGI auth middleware

## Key Conventions

- Tests must NOT contain `__init__.py` files (enforced by `check_test_inits` nox session)
- Test order is randomised via [pytest-random-order](https://github.com/pytest-dev/pytest-random-order) (`addopts = "--random-order"`), so both modules and the tests within them run in a shuffled order to surface hidden inter-test dependencies. The seed is printed in the pytest header; reproduce a specific order with `pytest --random-order-seed=<N>`. Tests must therefore be isolation-safe; quarantine a genuinely order-dependent module with `pytestmark = pytest.mark.random_order(disabled=True)` only as a last resort.
- Test conftest sets `BFABRICPY_CONFIG_ENV=__MOCK` to avoid real credentials
- Tests use the pytest-mock `mocker` fixture for **all** mocking — do not `import unittest.mock`.
  Use `mocker.patch(...)`, `mocker.patch.object(...)`, `mocker.patch.dict(...)`, `mocker.MagicMock()`,
  `mocker.Mock()`, `mocker.mock_open(...)`, etc. (`pytest-mock` is a test dependency in every package.)
- Group related tests in a file with plain `class TestXyz:` blocks — do **not** use `# --- section ---`
  comment banners as separators. A bare class (no base) is all pytest needs; move fixtures used by only
  one group inside its class so their scope matches the grouping. Keep each method name specific enough to
  read on its own (drop a prefix only when the class already conveys it).
- Ruff linting is currently only enforced on the `bfabric` package (scripts, wrapper_creator, tests, noxfile are excluded via per-file-ignores)
- Line length: 120 (ruff and black)
- Do not restate a parameter's default value in its docstring when the signature already shows it (e.g. `client_id: str = DEFAULT_CLIENT_ID`). Writing `(default "CLI")` in the `:param:` line just duplicates the signature and drifts out of sync when the default changes. Keep notes that explain what a value *means* (e.g. `(``0`` = auto-assign)`), not ones that merely repeat it. This also applies to class/model docstrings that restate a field's default shown a few lines below (prefer "see `field_name`" over repeating the literal value). Note the common case where the signature default is a sentinel like `None` but the docstring explains what it resolves to at runtime (e.g. `max_results: int | None = 100` documented as `` (``None`` for all) ``, or `path: Path | None = None` documented as `` (``None`` writes to ``./output.yml``) ``) — that is the *meaning* case, not the restatement case, and should be kept; phrase it as "``None`` does/means X", not "(default: X)", so it isn't mistaken for a literal restatement.
- basedpyright uses per-package baseline files at `.basedpyright/baseline.{package}.json` — **do not edit baseline files to silence new errors**; fix the code or add a targeted `# pyright: ignore[...]` comment on the offending line. Baselines only exist to grandfather in pre-existing errors.
- Integration tests live in a separate repository
- Use TDD: write a failing test first, verify it fails, then fix the code, then verify the test passes

## Releases

Each package is versioned and released independently (own `pyproject.toml` version, own `docs/changelog.md`, own `<package>/<version>` git tag). Preparing a release means: bump the `version` in that package's `pyproject.toml` and promote its changelog `[Unreleased]` section to a dated version heading. The release pipeline extracts the changelog section matching the tag and publishes it as the GitHub release notes.

Release-candidate (rc) convention — decided 2026-07-15:

- **One cumulative pre-release entry, not a stack.** While a version is in RC, keep a *single* changelog entry for it (e.g. `## [1.20.0rc2]`) that describes the **full** changeset for the upcoming `X.Y.0`. When cutting the next RC, re-date and extend that same entry and bump the `rcN` suffix — do **not** add a separate `[…rcN]` heading below the previous one. Per-RC history is preserved by the already-published git tags and GitHub releases, so the in-repo changelog doesn't need to re-keep it.
- **Flat, abbreviated bullets, headline-first.** RC entries merge the `Added`/`Changed`/`Fixed` subsections into one abbreviated bullet list, ordered with the user-facing headline changes first. Group dev-facing/typing/tooling changes (e.g. type-only fixes, ruff config, dead-code removal) under a trailing `Internal:` bullet so they don't crowd the main things. The detailed, structured notes live in git history and the GitHub release; the changelog entry is a quick-review summary.
- **Graduation.** When the RC becomes final, rename the `[X.Y.0rcN]` heading to `[X.Y.0]` with the release date (no content merge needed, since it was cumulative).
- **Cross-package dependency floors.** When a package uses a feature from an unreleased/RC `bfabric`, pin its floor to the rc (e.g. `bfabric>=1.20.0rc2,<1.21`). A plain `>=1.20.0` **excludes** `1.20.0rc2` under PEP 440, and naming a prerelease in the specifier is also what lets pip/uv resolve to it.

Hotfix convention (patch release of an older line) — decided 2026-07-24:

- **Branch from the version tag, not `main`/`release`.** When the newest line is unreleased or in RC, `release`/`main` have moved ahead, so a patch of the last stable (e.g. `1.19.1` while `main` is `1.20.0rc`) must be cut from that stable tag: `git checkout -b hotfix/<pkg>-X.Y.Z <pkg>/X.Y.(Z-1)`.
- **The hotfix branch is authoritative for its release.** Bump the patch version and add the `## [X.Y.Z]` changelog section there. This is what the pipeline extracts into the `<pkg>/X.Y.Z` tag and GitHub Release — the canonical record of what shipped.
- **Publish out-of-band, don't merge into `release`.** Merging a hotfix into `release` (ahead on a newer line) would mislabel that tree. Instead trigger the publish workflow against the hotfix ref: `gh workflow run publish_release.yml --ref hotfix/<pkg>-X.Y.Z -f environment=production -f force_packages=<pkg>`. The branch then lives on as the release record; it has no merge target.
- **Forward-port the fix to `main` as a normal PR, `[Unreleased]` only.** Cherry-pick the fix (`git cherry-pick -x`) so `1.X.0` doesn't regress. On `main` the entry stays under `[Unreleased]` with an inline note (e.g. "(also released as the X.Y.Z hotfix)") — do **not** backfill a `## [X.Y.Z]` section into `main`. A past-line patch can't sit in `main`'s version-descending changelog without breaking either version or date order, and it would duplicate the bullet; the tag + GitHub Release are where `X.Y.Z` is recorded.

## Branches

- `main` — active development
- `release` — triggers PyPI publish on merge
- When pushing, give the remote branch a reasonable, descriptive name even if the local branch has an auto-generated worktree name (e.g. `worktree-quiet-gathering-mitten`) — push with an explicit remote ref: `git push -u origin HEAD:feature/short-descriptive-name`.
