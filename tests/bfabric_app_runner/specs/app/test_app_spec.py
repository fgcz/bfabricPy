from pathlib import Path

import pytest

from bfabric_app_runner.specs.app.app_spec import AppSpec


@pytest.fixture()
def parsed():
    app_yaml = Path(__file__).parent / "test_versions.yml"
    return AppSpec.load_yaml(app_yaml=app_yaml, app_id="1000", app_name="yyy")


class TestVersions:
    @staticmethod
    def test_available_versions(parsed):
        assert parsed.available_versions == {"0.1.0", "0.1.1", "1.0.0", "1.0.1"}

    @staticmethod
    def test_hardcoded_single_variant(parsed):
        assert parsed["0.1.0"].commands.dispatch.command == 'echo "0.1.0"'

    @staticmethod
    def test_parametric_single_variant(parsed):
        assert parsed["0.1.1"].commands.dispatch.command == 'echo "0.1.1"'

    @staticmethod
    def test_parametric_multiple_variants(parsed):
        assert parsed["1.0.0"].commands.dispatch.command == 'echo "1.0.0"'
        assert parsed["1.0.1"].commands.dispatch.command == 'echo "1.0.1"'

    @staticmethod
    def test_substitute_app_id(parsed):
        assert parsed["0.1.0"].commands.process.command == 'echo "1000"'

    @staticmethod
    def test_reject_duplicates(parsed):
        version = parsed["0.1.0"]
        with pytest.raises(ValueError) as e:
            AppSpec(bfabric=parsed.bfabric, versions=[version, version])
        assert "Duplicate versions found" in str(e.value)


class TestBfabricAppSpec:
    @staticmethod
    def test_app_runner_version(parsed):
        assert parsed.bfabric.app_runner == "0"

    @staticmethod
    def test_app_runner_workflow_template_step(parsed):
        assert parsed.bfabric.workflow_template_step_id == None


RELATIVE_PATHS_YAML = """
bfabric:
  app_runner: "0"
versions:
  - version: "1.0.0"
    commands:
      dispatch:
        type: exec
        command: bash ${app.dir}/hello.sh
        prepend_paths:
          - bin
          - /opt/global/bin
      process:
        type: python_env
        pylock: dist/${app.version}/pylock.toml
        command: -m app.process
        local_extra_deps:
          - dist/${app.version}/app-${app.version}-py3-none-any.whl
          - ~/wheels/extra.whl
      collect:
        type: docker
        image: image
        command: command
        mounts:
          work_dir_target: /work
          read_only:
            - [reference, /app/reference]
          writeable:
            - [/data/results, /app/results]
"""


class TestSpecRelativePaths:
    @staticmethod
    @pytest.fixture()
    def app_dir(tmp_path) -> Path:
        # tmp_path can be a symlink (e.g. /var -> /private/var on macOS), while the spec dir is resolved.
        return tmp_path.resolve()

    @staticmethod
    @pytest.fixture()
    def loaded(app_dir):
        app_yaml = app_dir / "app.yml"
        app_yaml.write_text(RELATIVE_PATHS_YAML)
        return AppSpec.load_yaml(app_yaml=app_yaml, app_id="1000", app_name="yyy")["1.0.0"]

    @staticmethod
    def test_pylock_is_resolved_after_interpolation(loaded, app_dir):
        assert loaded.commands.process.pylock == app_dir / "dist/1.0.0/pylock.toml"

    @staticmethod
    def test_local_extra_deps_are_resolved_and_expanded(loaded, app_dir):
        assert loaded.commands.process.local_extra_deps == [
            app_dir / "dist/1.0.0/app-1.0.0-py3-none-any.whl",
            Path.home() / "wheels/extra.whl",
        ]

    @staticmethod
    def test_prepend_paths_keeps_absolute_entries(loaded, app_dir):
        assert loaded.commands.dispatch.prepend_paths == [app_dir / "bin", Path("/opt/global/bin")]

    @staticmethod
    def test_mount_host_paths_are_resolved(loaded, app_dir):
        mounts = loaded.commands.collect.mounts
        assert mounts.read_only == [(app_dir / "reference", Path("/app/reference"))]
        assert mounts.writeable == [(Path("/data/results"), Path("/app/results"))]

    @staticmethod
    def test_mount_container_paths_are_untouched(loaded):
        assert loaded.commands.collect.mounts.work_dir_target == Path("/work")

    @staticmethod
    def test_app_dir_variable(loaded, app_dir):
        assert loaded.commands.dispatch.command == f"bash {app_dir}/hello.sh"
