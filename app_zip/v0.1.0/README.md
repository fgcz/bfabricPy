# Python App Zip Format 0.1.0

## Overview

The App Zip format describes a structure for packaging Python applications with their dependencies for easy and reproducible deployments.

## Structure

The app zip file is a zip file, containing the following structure:

```
app/
├── app_zip_version.txt                 # Version of the app zip format (e.g., "0.1.0")
├── pylock.toml                         # Dependency lock file (PEP-751)
├── package/
│   └── myapp-1.0.0-py3-none-any.whl    # Python wheel package
└── config/
    ├── app.yml                         # Application configuration (e.g. for bfabric-app-runner)
    └── python_version.txt              # Python version to use (e.g., "3.13")
```

The following files are currently required:

- `app/app_zip_version.txt`
- `app/pylock.toml`
- `app/python_version.txt`

For an app runner application we additionally require:

- `app/config/app.yml`

## Details

### Root Directory `/app`

All paths must be prefixed within the zip by `/app`.
Other structures within the zip are not allowed.

### Lock File `/app/pylock.toml`

The lock file is a [PEP 751](https://peps.python.org/pep-0751/) compliant lock file.

### Python version `/app/python_version.txt`

A text file containing a string of the exact Python version to use (e.g., "3.13").

### Package directory `/app/package`

- Wheel naming follows [PEP 427](https://peps.python.org/pep-0427/) (e.g., `myanalysis-1.0.0-py3-none-any.whl`)
- Installed after dependencies to avoid conflicts, but without resolving additional dependencies.

### Configuration Directory `/app/config`

For app runner apps there should be a file `/app/config/app.yml` that contains the configuration for the app runner.

## Implementation

### Deployment Process

1. Extract zip if needed (or if zip is newer than extracted directory)
2. Read Python version from `python_version.txt`
3. Create virtual environment with specified Python version
4. Install dependencies from `pylock.toml`
5. Install wheel package without re-resolving dependencies
6. Run desired application command in the activated environment

### Example implementation (uv)

Some notes for our current example implementation:

- Installed with `uv pip install --requirement pylock.toml`
- Must be installed before the wheel package (TODO this will need to be specified more precisely in the future)
- Installed with `uv pip install --offline --no-deps package/*.whl`
