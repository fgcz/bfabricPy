# BFabric App Runner Templates

Copier templates for creating BFabric app runner applications with proper structure, configuration, and workflow implementation.

## Quick Start - Development Mode

### Prerequisites

- `uv` (Python package manager)
- `copier` (template engine)
- `bfabric-app-runner` (for testing and deployment)

### Creating and Testing a New Application

1. **Generate from template:**

    ```bash
    uvx copier copy ~/code/bfabricPy/bfabric_app_runner/examples/template my_app
    # Enter your project name when prompted
    ```

2. **Test in development mode:**

    ```bash
    cd my_app
    uv lock -U
    uv export --no-emit-project --format pylock.toml > pylock.toml

    # Test with workunit
    bfabric-app-runner prepare workunit app.yml \
      --work-dir workdir \
      --workunit-ref <WORKUNIT_ID> \
      --read-only \
      --force-app-version devel
    ```

3. **Run the workflow:**

    ```bash
    cd workdir
    make dispatch    # Initialize workflow
    make inputs      # Prepare input data
    make process     # Execute main processing
    make stage       # (Optional) Stage results
    ```

## Moving to Production

Once you've tested your application in development mode, you can build it for production:

1. **Update version in pyproject.toml:**

    **Important**: Always increase the version number before creating a release. Do not reuse existing versions.

2. **Build the application:**

    ```bash
    bash release.bash
    ```

3. **Test the production build:**

    ```bash
    bfabric-app-runner prepare workunit app.yml \
      --work-dir workdir \
      --workunit-ref <WORKUNIT_ID> \
      --read-only
    ```

Production mode uses packaged wheel files from `dist/` with isolated dependencies, while development mode uses source code directly.

## Application Structure

```
my_app/
├── app.yml                 # Application configuration
├── pyproject.toml          # Python project configuration
├── release.bash           # Build script
├── src/my_app/
│   ├── Snakefile          # Snakemake workflow definition
│   ├── workflow_params.py # Workflow parameters
│   ├── integrations/bfabric/
│   │   ├── dispatch.py    # Workflow dispatch logic
│   │   └── process.py     # Main processing entry point
│   └── steps/             # Processing utilities
└── dist/                  # Built packages (after release.bash)
```

## Configuration

- **app.yml**: Application metadata, version, and environment setup
- **workflow_params.py**: Input patterns, processing parameters, and output specifications

## Testing

Run the test suite:

```bash
.venv/bin/pytest test_template.py -v
```

## Make Commands

In the workdir after preparing a workunit:

- `make dispatch` - Initialize the workflow
- `make inputs` - Prepare input data
- `make process` - Execute Snakemake workflow
- `make stage` - Stage results for upload

## Customization

1. Add new processing steps in `src/my_app/steps/`
2. Update the Snakefile with new rules
3. Modify dependencies in `pyproject.toml` and run `uv lock -U`
4. Test in development mode before building for production
