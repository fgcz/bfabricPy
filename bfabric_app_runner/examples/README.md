# BFabric App Runner Templates

This directory contains Copier templates for creating BFabric app runner applications.

## Overview

The templates help you quickly scaffold new BFabric applications with the proper structure, configuration, and workflow implementation. Each generated application includes:

- **Complete project structure** with proper Python packaging
- **BFabric integration** with dispatch and process modules
- **Snakemake workflow** for data processing
- **Configuration management** for both development and production
- **Build system** with automated packaging and dependency management

## Quick Start

### Prerequisites

- `uv` (Python package manager)
- `copier` (template engine)
- `bfabric-app-runner` (for testing and deployment)

### Creating a New Application

1. **Generate from template:**

    ```bash
    uvx copier copy ~/code/bfabricPy/bfabric_app_runner/examples/template my_app
    # Enter your project name when prompted
    ```

2. **Build the application:**

    ```bash
    cd my_app
    bash release.bash
    ```

3. **Test with a workunit:**

    ```bash
    cd ..
    bfabric-app-runner prepare workunit my_app/app.yml \
      --work-dir workdir \
      --workunit-ref <WORKUNIT_ID> \
      --read-only
    ```

4. **Run the workflow:**

    ```bash
    cd workdir
    make dispatch    # Initialize workflow
    make inputs      # Prepare input data
    make process     # Execute main processing
    make stage       # (Optional) Stage results
    ```

## Application Structure

Generated applications follow this structure:

```
my_app/
├── app.yml                 # Application configuration
├── pyproject.toml          # Python project configuration
├── release.bash           # Build script
├── noxfile.py             # Task automation
├── src/my_app/
│   ├── __init__.py
│   ├── Snakefile          # Snakemake workflow definition
│   ├── workflow_params.py # Workflow parameters
│   ├── integrations/
│   │   └── bfabric/
│   │       ├── dispatch.py    # Workflow dispatch logic
│   │       └── process.py     # Main processing entry point
│   └── steps/
│       ├── collect_info.py      # Data collection utilities
│       └── compute_file_info.py # File processing utilities
└── dist/                  # Built packages (after release.bash)
```

## Development vs Production

The template supports two deployment modes:

### Production Mode (version 0.0.1)

- Uses packaged wheel files from `dist/`
- Isolated dependencies via `pylock.toml`
- Suitable for production deployment

### Development Mode (version devel)

- Uses source code directly
- Refreshes environment on each run
- Ideal for development and testing

## Configuration

### Application Configuration (`app.yml`)

The `app.yml` file defines:

- Application metadata and version
- Environment setup for each version
- Command specifications for dispatch and process
- Dependency management configuration

### Workflow Parameters

Edit `src/my_app/workflow_params.py` to configure:

- Input file patterns
- Processing parameters
- Output specifications

## Development Workflow

1. **Make changes** to your application code

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

3. **Run tests:**

    ```bash
    # Run the automated test suite
    .venv/bin/pytest test_template.py -v
    ```

4. **Build for production:**

    ```bash
    bash release.bash
    ```

## Testing

The `test_template.py` file provides comprehensive testing:

- **Template generation** testing
- **Build process** validation
- **Workunit preparation** for both modes
- **End-to-end workflow** execution
- **Output validation** checking

Run tests with:

```bash
.venv/bin/pytest test_template.py -v
```

## Make Commands

Once a workunit is prepared, use these commands in the workdir:

- `make dispatch` - Initialize the workflow and generate chunk definitions
- `make inputs` - Prepare and validate input data
- `make process` - Execute the main Snakemake workflow
- `make stage` - (Optional) Stage results for upload

For development, run commands individually to debug issues. For production, you can run them all at once:

```bash
make dispatch inputs process stage
```

## Customization

### Adding New Processing Steps

1. Create new Python modules in `src/my_app/steps/`
2. Update the Snakefile to include new rules
3. Modify `workflow_params.py` if needed
4. Test with development mode before building

### Modifying Dependencies

1. Update `pyproject.toml` with new dependencies
2. Run `uv lock -U` to update lock file
3. Test in development mode
4. Rebuild with `bash release.bash`

## Troubleshooting

### Common Issues

- **Missing pylock.toml**: Ensure you run `bash release.bash` for production or export pylock.toml for development
- **Path resolution errors**: Check that absolute paths are correctly generated in app.yml
- **Environment setup failures**: Verify `uv` is installed and accessible
- **Make command failures**: Check that the workunit was prepared successfully

### Debug Output

Set `BFABRICPY_CONFIG_ENV=TEST` to use test configuration and enable debug logging.

## Contributing

When modifying templates:

1. Update the template files in `template/`
2. Run the test suite to verify changes
3. Update this README if needed
4. Test with both development and production modes
