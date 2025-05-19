# Python App Zip Format 0.1.0

## Overview

The App Zip format describes a structure for packaging Python applications with their dependencies for easy and reproducible deployments.
This specification defines the required structure, validation rules, and deployment process.

## Structure

The app zip file is a standard ZIP archive, containing the following structure:

```
app/
├── app_zip_version.txt                 # Version of the app zip format (e.g., "0.1.0")
├── pylock.toml                         # Dependency lock file (PEP-751)
├── python_version.txt                  # Python version to use (e.g., "3.13")
├── package/
│   ├── myapp-1.0.0-py3-none-any.whl    # Primary application wheel package (optional)
│   └── dep1-2.0.0-py3-none-any.whl     # Optional additional wheels
└── config/
    └── app.yml                         # Application configuration (optional)
```

### Required Components

For a valid App Zip file, the following components are mandatory:

- `app/app_zip_version.txt` - Must contain exactly the string "0.1.0" for this version
- `app/pylock.toml` - Must be a valid PEP-751 compliant lock file
- `app/python_version.txt` - Must contain a valid Python version string

### Optional Components

- `app/package/` - Directory for wheel files (.whl)
- `app/config/app.yml` - Required for app runner applications; optional otherwise

### Path Requirements

- All files MUST be contained within the `app/` directory
- Directory structure must match exactly as specified (no additional directories)

## Component Details

### Version File (`app/app_zip_version.txt`)

- Must contain the exact string "0.1.0" (for this specification version)
- Whitespace trimming is permitted (leading/trailing spaces, newlines)
- No other content is allowed

### Python Version File (`app/python_version.txt`)

- Must contain a valid Python version string that follows PEP 440
- Exact versions only (e.g., "3.13", "3.12.1") are supported
- Version ranges or comparison operators are not supported
- Implementation must use exactly this Python version for the virtual environment

### Lock File (`app/pylock.toml`)

- Must comply with [PEP 751](https://peps.python.org/pep-0751/)
- Must contain all dependencies required by the application
- May reference external dependencies or direct references to wheel files in the package directory

### Package Directory (`app/package/`)

- Optional directory for wheel files
- May contain wheel files following [PEP 427](https://peps.python.org/pep-0427/) naming conventions
- All included wheel files must be valid and installable
- Files that are not valid wheel files (.whl) should be ignored

### Configuration Directory (`app/config/`)

- Optional for standard applications, required for app runner applications
- `app/config/app.yml` must be a valid app specification if provided

## Validation Rules

1. **Structure Validation:**

    - All required files and directories must be present
    - All files must be within the `app/` directory
    - No extraneous directories or files outside the specified structure

2. **Version Validation:**

    - `app_zip_version.txt` must contain "0.1.0"
    - `python_version.txt` must contain a valid Python version string

3. **Content Validation:**

    - `pylock.toml` must be a syntactically valid TOML file
    - If `app/config/app.yml` is present, it must be a valid YAML file
    - If wheel files are present, they must be valid according to PEP 427

## Deployment Process

An implementation of the App Zip format must follow these steps:

1. **Validation:**

    - Validate the structure and contents of the app zip file
    - If validation fails, exit with a non-zero status code and error message

2. **Extraction:**

    - Extract the zip file if needed
    - If the zip file is newer than the extracted directory, re-extract
    - Rely on the ZIP format for integrity verification

3. **Environment Creation:**

    - Read Python version from `python_version.txt`
    - Create a virtual environment with the exact specified Python version
    - If the specified Python version is not available, abort with error

4. **Dependency Installation:**

    - Install dependencies from `pylock.toml` first
    - If wheel files exist in the package directory, install them:
        - Use `--offline` mode to prevent network access
        - Use `--no-deps` to prevent resolving dependencies again

5. **Execution:**

    - Activate the virtual environment
    - Run the specified command within the activated environment

## Forward Compatibility

Future versions will use a new version string in `app_zip_version.txt`

## Implementation Notes

### Using `uv` Package Manager

For implementations using the `uv` package manager:

1. Create virtual environment:

    ```bash
    uv venv -p <python_version> .venv
    ```

2. Install dependencies:

    ```bash
    uv pip install --requirement pylock.toml
    ```

3. Install wheel files (if present):

    ```bash
    uv pip install --offline --no-deps package/*.whl
    ```

## Appendix: Changelog

### Version 0.1.0

- Initial specification

## Appendix: Example Implementation

See the `app_zip_tool.py` script for a reference implementation.
