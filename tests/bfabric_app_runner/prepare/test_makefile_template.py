import sys

import pytest

from bfabric_app_runner.prepare.makefile_template import (
    _is_valid_version,
    get_app_runner_dep_string,
    render_makefile_template,
    render_makefile,
)


class TestIsValidVersion:
    """Test version validation function."""

    @pytest.mark.parametrize("version", ["1.0.0", "2.1.3", "1.0.0-alpha", "1.0.dev0"])
    def test_valid_versions(self, version):
        """Test that valid versions are accepted."""
        assert _is_valid_version(version)

    @pytest.mark.parametrize(
        "version",
        [
            "git+https://github.com/user/repo.git",
            "not-a-version",
            "",
        ],
    )
    def test_invalid_versions(self, version):
        """Test that invalid versions are rejected."""
        assert not _is_valid_version(version)


class TestGetAppRunnerDepString:
    """Test dependency string generation."""

    def test_pypi_version_formatting(self):
        """Test that PyPI versions get == operator."""
        assert get_app_runner_dep_string("1.2.3") == "bfabric-app-runner==1.2.3"

    def test_git_reference_formatting(self):
        """Test that git references get @ operator."""
        git_ref = "git+https://github.com/fgcz/bfabricPy@main"
        assert get_app_runner_dep_string(git_ref) == f"bfabric-app-runner@{git_ref}"


class TestRenderMakefileTemplate:
    """Test template rendering functionality."""

    def test_template_substitution(self):
        """Test that template placeholders are correctly replaced."""
        template = "PYTHON_VERSION := @PYTHON_VERSION@\nAPP_RUNNER := @APP_RUNNER_DEP_STRING@"

        result = render_makefile_template(
            template=template, app_runner_dep_string="bfabric-app-runner==1.2.3", python_version="3.11"
        )

        assert "PYTHON_VERSION := 3.11" in result
        assert "APP_RUNNER := bfabric-app-runner==1.2.3" in result

    def test_hash_escaping(self):
        """Test that # characters are properly escaped."""
        template = "DEPENDENCY := @APP_RUNNER_DEP_STRING@"
        git_ref = "bfabric-app-runner@git+https://github.com/user/repo#subdirectory=subdir"
        result = render_makefile_template(template=template, app_runner_dep_string=git_ref, python_version="3.11")
        assert "\\#subdirectory=subdir" in result


class TestRenderMakefile:
    """Test the complete makefile rendering process."""

    def test_makefile_creation(self, mocker, tmp_path):
        """Test that makefile is created correctly."""
        mock_template = "PYTHON_VERSION := @PYTHON_VERSION@\nAPP_RUNNER := @APP_RUNNER_DEP_STRING@"
        mocker.patch(
            "bfabric_app_runner.prepare.makefile_template.importlib.resources.read_text", return_value=mock_template
        )

        mock_spec = mocker.Mock()
        mock_spec.app_runner = "1.5.0"
        makefile_path = tmp_path / "Makefile"
        render_makefile(makefile_path, mock_spec, rename_existing=True)

        assert makefile_path.exists()
        content = makefile_path.read_text()
        assert f"PYTHON_VERSION := {sys.version_info[0]}.{sys.version_info[1]}" in content
        assert "APP_RUNNER := bfabric-app-runner==1.5.0" in content

    def test_makefile_with_git_reference(self, mocker, tmp_path):
        """Test makefile generation with git reference."""
        mock_template = "DEP := @APP_RUNNER_DEP_STRING@"
        mocker.patch(
            "bfabric_app_runner.prepare.makefile_template.importlib.resources.read_text", return_value=mock_template
        )

        mock_spec = mocker.Mock()
        mock_spec.app_runner = "git+https://github.com/user/repo@branch#subdirectory=subdir"

        makefile_path = tmp_path / "Makefile"

        render_makefile(makefile_path, mock_spec, rename_existing=True)

        content = makefile_path.read_text()
        assert "\\#subdirectory=subdir" in content
