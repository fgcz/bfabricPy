# CommandPythonEnv System Documentation

## Overview

CommandPythonEnv is a system for creating, managing, and executing Python virtual environments. It supports both cached (persistent) and ephemeral (temporary) environments, with mechanisms for dependency installation, environment provisioning, and command execution.

## Environment Paths

### Base Cache Directory

- Primary location: `$XDG_CACHE_HOME/bfabric_app_runner/` (defaults to `~/.cache/bfabric_app_runner/` if XDG_CACHE_HOME is not set)

### Environment Types

1. **Cached Environments**

    - Path: `$XDG_CACHE_HOME/bfabric_app_runner/envs/<environment_hash>`
    - The environment hash is generated based on:
        - Hostname
        - Python version
        - Absolute path to pylock file
        - Modification time of pylock file
        - Absolute paths of any local extra dependencies (if present)

2. **Ephemeral Environments**

    - Path: `$XDG_CACHE_HOME/bfabric_app_runner/ephemeral/env_<random_suffix>`
    - Created as temporary directories
    - Cleaned up after use

### Environment Structure

- Python executable: `<env_path>/bin/python`
- Bin directory: `<env_path>/bin/`
- Provisioned marker: `<env_path>/.provisioned`
- Lock file (for cached envs): `<env_path>.lock`

## Core Logic Flow

1. **Environment Selection**

    - If `refresh` flag is enabled → Use ephemeral environment
    - Otherwise → Use cached environment

2. **Environment Resolution**

    - For cached environments:

        - Generate environment hash
        - Check if environment exists at hash path
        - Use file locking to prevent race conditions
        - Provision if not already provisioned

    - For ephemeral environments:

        - Create a new temporary directory
        - Always provision from scratch
        - Clean up after use

3. **Environment Provisioning Process**

    - Create virtual environment using `uv venv` with specified Python version
    - Install dependencies from pylock file using `uv pip install`
    - Install any local extra dependencies with `--no-deps` (if specified)
    - Mark as provisioned by creating `.provisioned` file

4. **Command Execution**

    - Use the environment's Python executable to run the command
    - Add the environment's bin directory to the PATH
    - Execute with any additional arguments passed to the command

## Key Behaviors

1. **Caching Strategy**

    - Environments are identified by their hash, allowing reuse
    - File locking prevents concurrent provisioning of the same environment
    - The `.provisioned` marker ensures partially-provisioned environments are not used

2. **Refresh Mode**

    - When enabled, creates a new ephemeral environment for each execution
    - Ensures clean environments for testing or when dependencies need updating
    - Automatically cleans up after execution

3. **Path Management**

    - Environment's bin directory is prepended to PATH during execution
    - Additional prepend_paths can be specified in the command

4. **Dependency Installation**

    - Uses `uv pip install` for fast, reliable dependency installation
    - Supports reinstallation of packages with the refresh flag
    - Handles local extra dependencies separately with `--no-deps`
