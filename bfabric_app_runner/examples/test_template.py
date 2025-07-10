"""Test script for the bfabric app runner copier template.

This script automates the testing process described in the README.md file.
"""

import os
import subprocess
from pathlib import Path
from pytest_mock import MockerFixture
import pytest
from collections.abc import Generator

WORKUNIT_ID = 324801


@pytest.fixture
def temp_test_dir(mocker: MockerFixture, tmpdir: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    test_dir = Path(tmpdir) / "bfabric_app_test"
    test_dir.mkdir()
    mocker.patch.dict("os.environ", {"BFABRICPY_CONFIG_ENV": "TEST"})
    monkeypatch.chdir(test_dir)
    yield test_dir


@pytest.fixture
def hello_app(temp_test_dir: Path) -> Path:
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
    subprocess.run(cmd, check=True)
    return Path(temp_test_dir) / "hello1"


def test_copier_template_creation(hello_app: Path) -> None:
    """Test creating a new app from the copier template."""
    assert hello_app.exists()
    assert (hello_app / "app.yml").exists()
    assert (hello_app / "release.bash").exists()


def test_template_structure(hello_app: Path) -> None:
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


def test_app_build_process(hello_app: Path) -> None:
    """Test building the app using release.bash."""
    os.chdir(hello_app)
    subprocess.run(["bash", "release.bash"], check=True)
    assert (hello_app / "app.yml").exists()
    assert (hello_app / "dist" / "0.0.1" / "pylock.toml").exists()
    assert (hello_app / "dist" / "0.0.1" / "hello1-0.0.1-py3-none-any.whl").exists()


def _prepare_app_for_version(hello_app: Path, app_version: str) -> None:
    """Prepare app for the specified version (build for release, export pylock for devel)."""
    os.chdir(hello_app)

    if app_version == "0.0.1":
        subprocess.run(["bash", "release.bash"], check=True)
        assert (hello_app / "dist" / "0.0.1" / "pylock.toml").exists(), "pylock.toml missing after build"
    else:
        subprocess.run(["uv", "lock", "-U"], check=True)
        with Path("pylock.toml").open("w") as f:
            subprocess.run(
                ["uv", "export", "--no-emit-project", "--format", "pylock.toml"],
                stdout=f,
                check=True,
            )
        assert (hello_app / "pylock.toml").exists(), "pylock.toml missing for devel version"


def _prepare_workunit(hello_app: Path, workdir: Path, app_version: str) -> None:
    """Prepare workunit using bfabric-app-runner."""
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


@pytest.mark.parametrize("app_version", ["0.0.1", "devel"])
def test_make_commands_workflow(hello_app: Path, app_version: str) -> None:
    """Test the complete make commands workflow for both release and devel versions."""
    # Step 1: Prepare the app (build or export pylock.toml)
    _prepare_app_for_version(hello_app, app_version)

    # Step 2: Prepare the workunit
    workdir = hello_app.parent / f"workdir_{app_version}"
    _prepare_workunit(hello_app, workdir, app_version)

    # Step 3: Run make commands in workdir
    os.chdir(workdir)
    make_commands = ["dispatch", "inputs", "process"]

    for command in make_commands:
        subprocess.run(["make", command], check=True)

    # Step 4: Validate results
    assert workdir.exists()
    assert (workdir / "Makefile").exists()

    work_dir = workdir / "work"
    outputs_yml = work_dir / "outputs.yml"
    assert outputs_yml.exists(), f"outputs.yml not found at {outputs_yml}"

    subprocess.run(["bfabric-app-runner", "validate", "outputs-spec", str(outputs_yml)], check=True)
