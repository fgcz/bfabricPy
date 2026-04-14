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

### Type Checking
```bash
nox -s basedpyright(bfabric)
nox -s basedpyright(bfabric_scripts)
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
- **`engine/`** — Strategy pattern for SOAP transport: `EngineSUDS` (default, suds library) and `EngineZeep` (zeep library). Both implement the same read/save/delete interface.
- **`entities/`** — Entity models with `HasOne`/`HasMany` relationship descriptors and lazy loading. `EntityReader` provides ORM-like access with caching (`cache_entities()` context manager).
- **`results/`** — `ResultContainer` wraps API responses with pagination, error handling, and `to_polars()` conversion.
- **`utils/cli_integration.py`** — `@use_client` decorator for CLI commands: auto-creates `Bfabric` client, injects config_env/config_file parameters.

### CLI (`bfabric_scripts/src/bfabric_scripts/cli/`)

Modern CLI built with **cyclopts**: `bfabric-cli api|dataset|executable|workunit|feeder|external-job`. Legacy scripts (`bfabric_read.py`, etc.) are preserved as entry points.

### App Runner (`bfabric_app_runner/`)

Handles dispatch → process → collect workflow for B-Fabric applications. Uses pydantic for spec validation, mako for templating.

## Key Conventions

- Tests must NOT contain `__init__.py` files (enforced by `check_test_inits` nox session)
- Test conftest sets `BFABRICPY_CONFIG_ENV=__MOCK` to avoid real credentials
- Ruff linting is currently only enforced on the `bfabric` package (scripts, wrapper_creator, tests, noxfile are excluded via per-file-ignores)
- Line length: 120 (ruff and black)
- basedpyright uses per-package baseline files at `.basedpyright/baseline.{package}.json`
- Integration tests live in a separate repository

## Branches

- `main` — active development
- `release` — triggers PyPI publish on merge
