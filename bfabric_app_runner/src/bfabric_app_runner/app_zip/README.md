# Python App Zip Format

## Overview

The App Zip format is a standardized structure for packaging Python applications with their dependencies for easy deployment in LIMS environments.

## Structure

```
app/
├── pylock.toml             # Dependency lock file (PEP-751)
├── package/
│   └── app-version.whl     # Python wheel package
└── config/
    ├── app.yml             # Application configuration
    └── python_version.txt  # Python version to use
```

## Component Semantics

### Root Directory

- `app/`: Fixed name to provide consistent deployment paths

### Lock File

- `pylock.toml`: PEP-751 compliant lock file containing all dependencies
- Installed with `uv pip install --requirement pylock.toml`
- Must be installed before the wheel package

### Package Directory

- `package/`: Contains the wheel file(s) for the application
- Wheel naming follows standard Python conventions (e.g., `myanalysis-1.0.0-py3-none-any.whl`)
- Installed with `uv pip install --offline --no-deps package/*.whl`
- Installed after dependencies to avoid conflicts

### Configuration Directory

- `config/`: Contains configuration files needed for the application
- `app.yml`: Application-specific configuration (varies by app)
- `python_version.txt`: Simple text file containing the exact Python version to use (e.g., "3.13")

## Deployment Process

1. Extract zip if needed (or if zip is newer than extracted directory)
2. Read Python version from `config/python_version.txt`
3. Create virtual environment with specified Python version
4. Install dependencies from `pylock.toml`
5. Install wheel package without re-resolving dependencies
6. Run desired application command in the activated environment

## Version Semantics

- Zip filename includes app name and version (e.g., `myanalysis-1.0.0.zip`)
- Python version is specified as a simple version string without constraints
- Wheel version follows PEP-440 versioning
