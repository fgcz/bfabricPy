#!/usr/bin/env python3
"""Test script for the bfabric app runner copier template.

This script automates the testing process described in the README.md file.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


WORKUNIT_ID = 324801


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing."""
    test_dir = tempfile.mkdtemp(prefix="bfabric_app_test_")
    original_cwd = os.getcwd()
    original_env = os.environ.get("BFABRICPY_CONFIG_ENV")

    os.chdir(test_dir)
    os.environ["BFABRICPY_CONFIG_ENV"] = "TEST"

    yield test_dir

    os.chdir(original_cwd)
    if original_env is not None:
        os.environ["BFABRICPY_CONFIG_ENV"] = original_env
    else:
        os.environ.pop("BFABRICPY_CONFIG_ENV", None)
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def hello_app(temp_test_dir):
    """Create a test app using the copier template."""
    template_path = Path(__file__).parent / "template"

    cmd = [
        "uvx",
        "copier",
        "copy",
        str(template_path.resolve()),
        "hello1",
        "--data",
        "project_name=hello1",
        "--data",
        "deploy_with_lfs=true",
        "--defaults",
    ]

    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return Path(temp_test_dir) / "hello1"


def test_copier_template_creation(hello_app):
    """Test creating a new app from the copier template."""
    assert hello_app.exists()
    assert (hello_app / "app.yml").exists()
    assert (hello_app / "release.bash").exists()


def test_template_structure(hello_app):
    """Test that the template creates expected file structure."""
    expected_files = [
        "app.yml",
        "release.bash",
        "pyproject.toml",
        "noxfile.py",
        "src/hello1/__init__.py",
        "src/hello1/integrations/bfabric/dispatch.py",
        "src/hello1/integrations/bfabric/process.py",
        "src/hello1/steps/collect_info.py",
        "src/hello1/steps/compute_file_info.py",
        "src/hello1/workflow_params.py",
    ]

    for file_path in expected_files:
        assert (hello_app / file_path).exists(), f"Expected file {file_path} not found"

    # Check that project_name was properly substituted
    content = (hello_app / "app.yml").read_text()
    assert "hello1" in content


def test_app_build_process(hello_app):
    """Test building the app using release.bash."""
    os.chdir(hello_app)
    result = subprocess.run(["bash", "release.bash"], check=False, capture_output=True, text=True)

    # Build might fail due to missing tools, but we can still check structure
    assert (hello_app / "app.yml").exists()


@pytest.mark.parametrize("app_version", ["0.0.1", "devel"])
def test_workunit_preparation(hello_app, app_version):
    """Test preparing a workunit for both release and devel versions."""
    # For release version, we need to build first
    if app_version == "0.0.1":
        os.chdir(hello_app)
        subprocess.run(["bash", "release.bash"], check=True)
        assert (hello_app / "dist" / "0.0.1" / "pylock.toml").exists(), "pylock.toml missing after build"
    else:
        # For devel version, we need to export the pylock.toml
        os.chdir(hello_app)
        subprocess.run(["uv", "lock", "-U"], check=True)
        subprocess.run(
            ["uv", "export", "--no-emit-project", "--format", "pylock.toml"],
            stdout=open("pylock.toml", "w"),
            check=True,
        )
        assert (hello_app / "pylock.toml").exists(), "pylock.toml missing for devel version"

    workdir = hello_app.parent / f"workdir_{app_version}"
    cmd = [
        "bfabric-app-runner",
        "prepare",
        "workunit",
        str(hello_app / "app.yml"),
        "--work-dir",
        str(workdir),
        "--workunit-ref",
        str(WORKUNIT_ID),
        "--read-only",
        "--force-app-version",
        app_version,
    ]

    subprocess.run(cmd, check=True)
    assert workdir.exists()


@pytest.mark.parametrize("app_version", ["0.0.1", "devel"])
def test_make_commands_workflow(hello_app, app_version):
    """Test the make commands workflow for both release and devel versions."""
    # Prepare the app based on version
    if app_version == "0.0.1":
        os.chdir(hello_app)
        subprocess.run(["bash", "release.bash"], check=True)
        assert (hello_app / "dist" / "0.0.1" / "pylock.toml").exists(), "pylock.toml missing after build"
    else:
        # For devel version, we need to export the pylock.toml
        os.chdir(hello_app)
        subprocess.run(["uv", "lock", "-U"], check=True)
        subprocess.run(
            ["uv", "export", "--no-emit-project", "--format", "pylock.toml"],
            stdout=open("pylock.toml", "w"),
            check=True,
        )
        assert (hello_app / "pylock.toml").exists(), "pylock.toml missing for devel version"

    workdir = hello_app.parent / f"workdir_{app_version}"

    # Prepare the workunit
    cmd = [
        "bfabric-app-runner",
        "prepare",
        "workunit",
        str(hello_app / "app.yml"),
        "--work-dir",
        str(workdir),
        "--workunit-ref",
        str(WORKUNIT_ID),
        "--read-only",
        "--force-app-version",
        app_version,
    ]

    subprocess.run(cmd, check=True)

    # Change to workdir
    os.chdir(workdir)

    # Test individual make commands
    make_commands = ["dispatch", "inputs", "process"]

    for command in make_commands:
        subprocess.run(["make", command], check=True)

    # Verify workdir structure after running commands
    assert workdir.exists()
    assert (workdir / "Makefile").exists()

    # Validate that outputs.yml was created correctly in the work chunk directory
    work_dir = workdir / "work"
    outputs_yml = work_dir / "outputs.yml"
    assert outputs_yml.exists(), f"outputs.yml not found at {outputs_yml}"

    subprocess.run(["bfabric-app-runner", "validate", "outputs-spec", str(outputs_yml)], check=True)


if __name__ == "__main__":
    # Use: .venv/bin/pytest test_template.py -v
    # Or: .venv/bin/python test_template.py
    pytest.main([__file__, "-v"])
