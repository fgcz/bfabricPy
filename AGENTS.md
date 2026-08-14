# AGENTS.md

This file provides guidance to AI agents working with code in this repository. Every line of it is loaded into every session's context, so it has to earn that cost: add a rule only when an agent would otherwise get it wrong, keep it to one line, and prefer rewording an existing rule over appending a new one.

## Project Overview

bfabricPy is a Python client library for [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/), a data management platform at the Functional Genomics Center Zurich (FGCZ). It communicates with B-Fabric via SOAP/WSDL.

## Monorepo Structure

This is a **uv workspace** with 5 packages:

| Package              | Purpose                          | Min Python |
| -------------------- | -------------------------------- | ---------- |
| `bfabric`            | Core client library              | 3.11       |
| `bfabric_scripts`    | CLI scripts and utilities        | 3.11       |
| `bfabric_app_runner` | Application runner for workflows | 3.12       |
| `bfabric_rest_proxy` | FastAPI REST proxy               | 3.12       |
| `bfabric_asgi_auth`  | ASGI auth middleware             | 3.13       |

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

Run each package's suite in a **separate** `pytest` invocation, as nox does — one invocation over two package trees fails at collection because identically-named test modules collide (see the `__init__.py` convention below).

### Type Checking

```bash
nox -s basedpyright(bfabric)
nox -s basedpyright(bfabric_scripts)
nox -s basedpyright(bfabric_app_runner)
```

### Linting and formatting

```bash
nox -s code_style                      # ruff lint via nox — lint only, checks no formatting
ruff check bfabric                     # ruff directly
pre-commit run --all-files             # the formatter gate (black, blacken-docs for md code blocks, mdformat for md)
```

**black is the formatter — never run `ruff format`.** It disagrees with black on ~15 files and produces a large spurious diff. Since neither `nox -s code_style` nor CI checks formatting, the pre-commit hook rejecting the commit is the only thing that catches a wrong formatter.

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

Docs live alongside each package's source; skim the index when working in one. `bfabric/docs/index.md` and `bfabric_app_runner/docs/index.md` are full sites (getting started, user guides, API reference, design) and the only two that `nox -s docs` builds. `bfabric_scripts`, `bfabric_rest_proxy` and `bfabric_asgi_auth` have just a `docs/changelog.md`, plus a `README.md` for the latter two.

## Key Conventions

### Tests

- Tests must NOT contain `__init__.py` files (enforced by the `check_test_inits` nox session).
- Test order is randomised via [pytest-random-order](https://github.com/pytest-dev/pytest-random-order) (`addopts = "--random-order"`), so tests must be isolation-safe. The seed is printed in the pytest header; reproduce an order with `pytest --random-order-seed=<N>`. Quarantine a genuinely order-dependent module with `pytestmark = pytest.mark.random_order(disabled=True)` only as a last resort.
- Test conftest sets `BFABRICPY_CONFIG_ENV=__MOCK` to avoid real credentials.
- Use the pytest-mock `mocker` fixture for **all** mocking — do not `import unittest.mock`.
- Group related tests with plain `class TestXyz:` blocks (no base class needed), not `# --- section ---` comment banners. Move fixtures used by only one group inside its class. Keep method names specific enough to read on their own.
- Integration tests live in a separate repository.
- Use TDD: write a failing test first, verify it fails, then fix the code, then verify the test passes.

### Style and typing

- Line length is 120 (ruff and black). Ruff lint is currently only enforced on the `bfabric` package (scripts, wrapper_creator, tests, noxfile are excluded via per-file-ignores).
- basedpyright uses per-package baseline files at `.basedpyright/baseline.{package}.json` — **do not edit a baseline to silence a new error**; fix the code or add a targeted `# pyright: ignore[...]` on the offending line. Baselines only exist to grandfather in pre-existing errors.
- Docstrings use Sphinx `:param:` / `:raises:`; Google-style `Args:` / `Returns:` blocks survive in a few older modules (e.g. `entities/core/uri.py`) — don't add more.
- Keep docstrings at the lowest useful altitude: one summary line by default, plus a short paragraph only for a contract the signature cannot show (why this exists beside a similar function, a gotcha, an ordering constraint). Skip `Returns:` blocks and `:param:` lines that restate the annotation, and don't restate a default the signature already shows. Do document what a value *means* — a sentinel's runtime resolution (`` `None` reads all results ``, `` `None` writes to `./output.yml` ``) or a magic value (`` `0` = auto-assign ``) — phrased as "`None` does X", not "(default: X)".
- Avoid `>>>` examples: no session collects doctests, so they read as tested without being tested. Put a short example in the prose instead.
- Exception: a cyclopts command function's docstring **is** its `--help` text — the summary line becomes the command description and each `:param:` line becomes that option's help (see `bfabric-cli workunit not-available --help`). That is user-facing copy: keep it complete and clear, and trim the internal helpers around it instead.

## Changelog

Each package has its own `docs/changelog.md` following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/): `### Added` / `### Changed` / `### Fixed` / `### Removed` subsections under `## [Unreleased]`.

- One or two lines per entry: the symbol, and the effect a user sees. No code blocks, no before/after examples, no "previously it did X because Y" — rationale belongs in the commit message.
- Label an entry **Breaking** only when the API has real external consumers; otherwise just describe it in its new shape.
- Collect dev-facing typing/tooling changes into a single trailing `Internal:` bullet.
- Release-candidate entries are the one exception to the subsections (flat bullets, cumulative) — see [RELEASING.md](RELEASING.md).

## Pull requests

The body is a short changelog-style bullet list — one line per change a *user* would notice, phrased "Add/Change/Fix X to do Y" — and then it stops. No `##` section headings, no test plan or "Testing:" line, no background paragraph, no implementation notes. Omit internal refactors, docs, and tooling changes entirely; that detail belongs in the commit messages and the package changelog. If a caveat genuinely must be flagged, make it one more bullet, never a section.

`rel-*` release PRs get an empty body (`--body ""`): the pipeline publishes the changelog section as the release notes, so a body would only be a worse copy of it.

## Releases

Each package is versioned and released independently — own `pyproject.toml` version, own `docs/changelog.md`, own `<package>/<version>` git tag. Release preparation is **mechanics only** (version bumps, changelog graduation, dependency-pin updates) and must not introduce code changes; see the `rel-*` rule under [Branches](#branches).

The full procedure — the `rel-*` → `release` → `main` branch loop, the release-candidate and hotfix conventions, and how to verify a build offline before it ships — is in [RELEASING.md](RELEASING.md). Read it before touching a release.

## Branches

- `main` — active development
- `release` — pushing to it runs `publish_release.yml` and publishes to PyPI. Release-prep PRs target **this** branch, not `main`, and it is merged back into `main` afterwards.
- `rel-<date>-NN` — release-preparation branches, cut fresh from `origin/main`, carrying **only release mechanics** so the release ships exactly what is already on `origin/main`. Never merge feature or refactor work into one — new functionality lands on `origin/main` via its own PR and is picked up by a later cut. A genuine hotfix, on the user's explicit say-so, is named `hotfix-*` / `patch-*` instead so the intent is unambiguous.
- When pushing, give the remote branch a reasonable, descriptive name even if the local branch has an auto-generated worktree name (e.g. `worktree-quiet-gathering-mitten`) — push with an explicit remote ref: `git push -u origin HEAD:feature/short-descriptive-name`.
