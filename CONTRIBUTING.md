# Contributing

This page describes information relevant for contributing to bfabricPy.

## Monorepo Setup

The project is built in a single repository (uv workspace), which hosts 5 Python packages:

- `bfabric` - Core bfabric client library
- `bfabric_scripts` - CLI scripts and utilities
- `bfabric_app_runner` - Application runner for bfabric workflows
- `bfabric_rest_proxy` - REST API proxy
- `bfabric_asgi_auth` - ASGI authentication middleware

Each of these projects has its independent `pyproject.toml` and package structure.

### Workspace Dependencies

`bfabric_scripts`, `bfabric_app_runner`, `bfabric_rest_proxy`, and `bfabric_asgi_auth` depend on the `bfabric` package. The workspace configuration in `pyproject.toml` manages these dependencies using workspace references, allowing you to make changes to `bfabric` and have them immediately available to dependent packages without reinstalling.

### Direct References

[Direct references](https://peps.python.org/pep-0440/#direct-references) allow referencing a Git repository directly. This is useful during development when you add a new feature to `bfabric` and need it in `bfabric-scripts`, but don't want to deploy it yet.

**Note:** Direct references are primarily used in this monorepo context. For external dependencies, use the workspace setup described below.

If needed, direct references can be specified as:

- `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric`
- `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric_scripts`
- `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric_app_runner`
- `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric_rest_proxy`
- `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric_asgi_auth`

You can omit `@main` to use a specific branch or tag.

If you use `hatchling` as your `pyproject.toml` builder, ensure direct references are allowed:

```toml
[tool.hatch.metadata]
allow-direct-references = true
```

## Development Setup

The project uses [uv](https://github.com/astral-sh/uv) as its package manager and workspace tool.

### Prerequisites

1. Install Python 3.11 or 3.13
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/):
   ```bash
   # Using pip
   pip install uv

   # Or using the install script (Linux/Mac)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

### Setting Up the Development Environment

To set up the complete development environment with all packages and extras (including test dependencies):

```bash
uv sync --all-packages --all-extras
```

This command:

- Installs all workspace packages in editable mode
- Installs all optional dependency groups (`dev`, `test`, `doc`, etc.)
- Creates a `.venv` directory with the virtual environment
- Sets up workspace references so changes to `bfabric` are immediately available to dependent packages

### Activating the Environment

```bash
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

## Running Tests

### Using nox (Recommended)

The project uses [nox](https://nox.thea.codes/) for running tests in isolated environments. Nox uses `uv` as its backend, so you don't need to manually set up a virtual environment first.

Install nox:

```bash
pip install nox  # or uv pip install nox
```

Run tests for all packages:

```bash
nox
```

Run tests for a specific package:

```bash
nox -s test_bfabric
nox -s test_bfabric_scripts
nox -s test_bfabric_app_runner
```

Run tests with specific Python version and resolution strategy:

```bash
nox -s test_bfabric-3.13(highest)
nox -s test_bfabric-3.11(lowest-direct)
```

### Using pytest Directly

After activating your development environment (with `uv sync`), you can run pytest directly:

```bash
# Run all tests
pytest

# Run tests for a specific package
pytest tests/bfabric
pytest tests/bfabric_scripts
pytest tests/bfabric_app_runner

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/bfabric/test_client.py
```

## Code Quality

### Type Checking

Run type checking using basedpyright for all packages:

```bash
nox -s basedpyright
```

Run type checking for a specific package:

```bash
nox -s basedpyright(bfabric)
nox -s basedpyright(bfabric_scripts)
```

### Linting

Run Ruff linting:

```bash
nox -s code_style
```

Or run ruff directly:

```bash
ruff check bfabric
ruff check bfabric_scripts
```

## Documentation

We currently do not have a versioning solution for the documentation, but we can add that later once it is more mature.

### Preview Documentation Locally

To preview documentation while you write it:

```bash
# From the bfabric/docs directory
cd bfabric/docs
make html

# The output will be in _build/html/
# You can open _build/html/index.html in your browser
```

### Build All Documentation

```bash
nox -s docs
```

This builds documentation for `bfabric` and `bfabric_app_runner` and places the output in the `site/` directory.

### Publish Documentation

```bash
nox -s publish_docs
```

This publishes the documentation to GitHub Pages by updating the `gh-pages` branch.

## Integration Tests

Note that integration tests have been moved to a separate repository. Please contact us if you are interested in running them.

## Release Process

To create a release:

1. **Create a branch** from `main` (e.g., `deploy-yyyymmdd-01`)
2. **Update versions** in the relevant `pyproject.toml` files
3. **Update changelogs** with the new version number and date after the "Unreleased" section
4. **Create a PR** from your new branch to the `release` branch

Once the PR is ready:

5. **Wait for validation pipeline comments**:
   - One comment will list the package versions that will be updated
   - Another comment will confirm all tests have passed
6. **Merge the PR**

After merging:

7. **Wait for PyPI publish**: Your package will be built and sent to PyPI automatically
8. **Backport to main**: Create a PR from `release` to `main` to include the `pyproject.toml` changes and merge it ASAP
9. **Publish GitHub release**: If everything worked, the release should be pre-filled with the changelog notes. Create the release using the tag that was automatically created.

## Troubleshooting

### Workspace Issues

If you encounter issues with workspace dependencies, try resyncing:

```bash
uv sync --reinstall --all-packages --all-extras
```
