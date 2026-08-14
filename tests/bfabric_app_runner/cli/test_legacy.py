import stat

import pytest
import yaml
from bfabric_app_runner.cli.legacy import (
    UPLOAD_MANIFEST_FILENAME,
    cmd_legacy_collect,
    cmd_legacy_dispatch,
    cmd_legacy_run,
)
from bfabric_app_runner.specs.inputs.legacy_wrapper_yaml_spec import LegacyWrapperYamlSpec
from bfabric_app_runner.specs.inputs_spec import InputsSpec
from bfabric_app_runner.specs.outputs_spec import OutputsSpec


@pytest.fixture
def chunk_dir(tmp_path):
    chunk_dir = tmp_path / "work"
    chunk_dir.mkdir()
    return chunk_dir


def _write_config(chunk_dir, output_path, filename="config.yaml"):
    config = {"application": {"output": [str(output_path)], "protocol": "scp"}, "job_configuration": {}}
    (chunk_dir / filename).write_text(yaml.safe_dump(config))


def _record_upload(chunk_dir, path, content="payload"):
    """Stand in for the upload shim: create the file elsewhere and note it in the manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    manifest = chunk_dir / UPLOAD_MANIFEST_FILENAME
    with manifest.open("a") as handle:
        _ = handle.write(f"{path}\n")
    return path


class TestDispatch:
    @pytest.fixture
    def work_dir(self, tmp_path):
        work_dir = tmp_path / "WU349972"
        work_dir.mkdir()
        definition = {
            "execution": {"raw_parameters": {}, "resources": [3220134, 3220135]},
            "registration": {
                "application_id": 224,
                "application_name": "MaxQuant",
                "workunit_id": 349972,
                "workunit_name": "MaxQuant_Hi5_POI",
                "container_id": 42904,
                "container_type": "order",
                "storage_id": 2,
                "storage_output_folder": "p42904/bfabric/Proteomics/MaxQuant/2026/2026-08/2026-08-12",
            },
        }
        (work_dir / "workunit_definition.yml").write_text(yaml.safe_dump(definition))
        return work_dir

    def test_writes_a_single_chunk(self, work_dir):
        cmd_legacy_dispatch(work_dir / "workunit_definition.yml", work_dir, executable="/opt/legacy.bash")

        chunks = yaml.safe_load((work_dir / "chunks.yml").read_text())["chunks"]
        assert chunks == [str(work_dir / "work")]

    def test_inputs_hold_only_the_legacy_yaml(self, work_dir):
        """The legacy app fetches its own resources from the YAML, so nothing else is staged."""
        cmd_legacy_dispatch(work_dir / "workunit_definition.yml", work_dir, executable="/opt/legacy.bash")

        inputs = InputsSpec.read_yaml(work_dir / "work" / "inputs.yml").inputs
        assert len(inputs) == 1
        spec = inputs[0]
        assert isinstance(spec, LegacyWrapperYamlSpec)
        assert spec.workunit_id == 349972
        assert spec.executable == "/opt/legacy.bash"
        assert spec.filename == "config.yaml"

    def test_output_path_defaults_into_the_chunk_dir(self, work_dir):
        cmd_legacy_dispatch(work_dir / "workunit_definition.yml", work_dir, executable="/opt/legacy.bash")

        spec = InputsSpec.read_yaml(work_dir / "work" / "inputs.yml").inputs[0]
        assert spec.output_path == str(work_dir / "work" / "output-WU349972.zip")

    def test_output_filename_override(self, work_dir):
        cmd_legacy_dispatch(
            work_dir / "workunit_definition.yml",
            work_dir,
            executable="/opt/legacy.bash",
            output_filename="result.sf3",
        )

        spec = InputsSpec.read_yaml(work_dir / "work" / "inputs.yml").inputs[0]
        assert spec.output_path == str(work_dir / "work" / "result.sf3")

    def test_config_filename_override(self, work_dir):
        cmd_legacy_dispatch(
            work_dir / "workunit_definition.yml", work_dir, executable="/opt/legacy.bash", config_filename="legacy.yml"
        )

        assert InputsSpec.read_yaml(work_dir / "work" / "inputs.yml").inputs[0].filename == "legacy.yml"

    def test_definition_without_registration(self, work_dir):
        path = work_dir / "no_registration.yml"
        path.write_text(yaml.safe_dump({"execution": {"raw_parameters": {}}, "registration": None}))

        with pytest.raises(ValueError, match="has no registration section"):
            cmd_legacy_dispatch(path, work_dir, executable="/opt/legacy.bash")


class TestCollect:
    def test_declares_the_produced_output(self, chunk_dir):
        output = chunk_dir / "result.zip"
        output.write_text("payload")
        _write_config(chunk_dir, output)

        cmd_legacy_collect(chunk_dir)

        specs = OutputsSpec.read_yaml(chunk_dir / "outputs.yml")
        assert len(specs) == 1
        assert specs[0].local_path == output
        assert str(specs[0].store_entry_path) == "result.zip"

    def test_declares_uploads_in_place_alongside_the_output(self, chunk_dir, tmp_path):
        """Recorded uploads reach the same storage as the main output, without being copied first."""
        output = chunk_dir / "result.zip"
        output.write_text("payload")
        _write_config(chunk_dir, output)
        scratch = tmp_path / "scratch"
        _record_upload(chunk_dir, scratch / "proteinGroups.txt")
        _record_upload(chunk_dir, scratch / "specs.pdf")

        cmd_legacy_collect(chunk_dir)

        specs = OutputsSpec.read_yaml(chunk_dir / "outputs.yml")
        assert [str(spec.store_entry_path) for spec in specs] == ["result.zip", "proteinGroups.txt", "specs.pdf"]
        # referenced where the app left them, not relocated into the chunk directory
        assert specs[1].local_path == scratch / "proteinGroups.txt"

    def test_preserves_upload_order(self, chunk_dir, tmp_path):
        output = chunk_dir / "result.zip"
        output.write_text("payload")
        _write_config(chunk_dir, output)
        for name in ["specs.pdf", "parameters.txt", "proteinGroups.txt"]:
            _record_upload(chunk_dir, tmp_path / "scratch" / name)

        cmd_legacy_collect(chunk_dir)

        specs = OutputsSpec.read_yaml(chunk_dir / "outputs.yml")
        assert [str(spec.store_entry_path) for spec in specs[1:]] == [
            "specs.pdf",
            "parameters.txt",
            "proteinGroups.txt",
        ]

    def test_ignores_a_repeated_upload_of_the_same_path(self, chunk_dir, tmp_path):
        output = chunk_dir / "result.zip"
        output.write_text("payload")
        _write_config(chunk_dir, output)
        upload = tmp_path / "scratch" / "proteinGroups.txt"
        _record_upload(chunk_dir, upload)
        _record_upload(chunk_dir, upload)

        cmd_legacy_collect(chunk_dir)

        assert len(OutputsSpec.read_yaml(chunk_dir / "outputs.yml")) == 2

    def test_works_without_any_uploads(self, chunk_dir):
        output = chunk_dir / "result.zip"
        output.write_text("payload")
        _write_config(chunk_dir, output)

        cmd_legacy_collect(chunk_dir)

        assert len(OutputsSpec.read_yaml(chunk_dir / "outputs.yml")) == 1

    def test_rejects_two_uploads_sharing_a_resource_name(self, chunk_dir, tmp_path):
        output = chunk_dir / "result.zip"
        output.write_text("payload")
        _write_config(chunk_dir, output)
        _record_upload(chunk_dir, tmp_path / "a" / "proteinGroups.txt")
        _record_upload(chunk_dir, tmp_path / "b" / "proteinGroups.txt")

        with pytest.raises(ValueError, match="share a resource name: proteinGroups.txt"):
            cmd_legacy_collect(chunk_dir)

    def test_missing_output_and_no_uploads_fails(self, chunk_dir):
        _write_config(chunk_dir, chunk_dir / "result.zip")
        with pytest.raises(FileNotFoundError, match="did not produce its declared output"):
            cmd_legacy_collect(chunk_dir)

    def test_missing_output_with_uploads_registers_the_uploads(self, chunk_dir, tmp_path):
        """A few legacy apps only ever upload extra resources and never write the declared output."""
        _write_config(chunk_dir, chunk_dir / "result.zip")
        _record_upload(chunk_dir, tmp_path / "scratch" / "fgcz_MQ_QC_report.pdf")

        cmd_legacy_collect(chunk_dir)

        specs = OutputsSpec.read_yaml(chunk_dir / "outputs.yml")
        assert [str(spec.store_entry_path) for spec in specs] == ["fgcz_MQ_QC_report.pdf"]

    def test_recorded_upload_that_vanished(self, chunk_dir, tmp_path):
        output = chunk_dir / "result.zip"
        output.write_text("payload")
        _write_config(chunk_dir, output)
        upload = _record_upload(chunk_dir, tmp_path / "scratch" / "proteinGroups.txt")
        upload.unlink()

        with pytest.raises(FileNotFoundError, match="recorded by the app is gone"):
            cmd_legacy_collect(chunk_dir)

    def test_remote_output_is_rejected(self, chunk_dir):
        _write_config(chunk_dir, "bfabric@fgcz-ms.uzh.ch:/srv/www/htdocs/result.zip")
        with pytest.raises(ValueError, match="Cannot register the remote output"):
            cmd_legacy_collect(chunk_dir)

    def test_missing_config(self, chunk_dir):
        with pytest.raises(FileNotFoundError, match="No legacy configuration at"):
            cmd_legacy_collect(chunk_dir)

    def test_custom_config_filename(self, chunk_dir):
        output = chunk_dir / "result.zip"
        output.write_text("payload")
        _write_config(chunk_dir, output, filename="legacy.yml")
        cmd_legacy_collect(chunk_dir, config_filename="legacy.yml")
        assert (chunk_dir / "outputs.yml").is_file()


class TestRun:
    @pytest.fixture
    def legacy_app(self, tmp_path):
        """A stand-in legacy app exercising the argument, a no-op shim and the upload shim."""
        app = tmp_path / "legacy_app.sh"
        app.write_text(
            "#!/bin/sh\n"
            'echo "$1" > "$(dirname "$0")/received_argument"\n'
            'command -v bfabric_setWorkunitStatus_available.py > "$(dirname "$0")/resolved_command"\n'
            'echo extra > "$(dirname "$0")/proteinGroups.txt"\n'
            'bfabric_upload_resource.py "$(dirname "$0")/proteinGroups.txt" 349972\n'
        )
        app.chmod(app.stat().st_mode | stat.S_IXUSR)
        return app

    def test_passes_the_config_path(self, chunk_dir, legacy_app):
        _write_config(chunk_dir, chunk_dir / "result.zip")

        cmd_legacy_run(str(legacy_app), chunk_dir)

        assert (legacy_app.parent / "received_argument").read_text().strip() == str(chunk_dir / "config.yaml")

    def test_shim_shadows_the_real_status_command(self, chunk_dir, legacy_app):
        """bfabric_scripts installs the real command, so the shim only helps if it wins on PATH."""
        _write_config(chunk_dir, chunk_dir / "result.zip")

        cmd_legacy_run(str(legacy_app), chunk_dir)

        assert "app-runner-legacy-shims" in (legacy_app.parent / "resolved_command").read_text()

    def test_uploads_are_recorded_in_the_manifest(self, chunk_dir, legacy_app):
        _write_config(chunk_dir, chunk_dir / "result.zip")

        cmd_legacy_run(str(legacy_app), chunk_dir)

        manifest = (chunk_dir / UPLOAD_MANIFEST_FILENAME).read_text().splitlines()
        assert manifest == [str(legacy_app.parent / "proteinGroups.txt")]

    def test_missing_config(self, chunk_dir, legacy_app):
        with pytest.raises(FileNotFoundError, match="No legacy configuration at"):
            cmd_legacy_run(str(legacy_app), chunk_dir)

    def test_failing_app_raises(self, chunk_dir, tmp_path):
        failing = tmp_path / "failing.sh"
        failing.write_text("#!/bin/sh\nexit 3\n")
        failing.chmod(failing.stat().st_mode | stat.S_IXUSR)
        _write_config(chunk_dir, chunk_dir / "result.zip")

        with pytest.raises(Exception, match="returned non-zero exit status 3"):
            cmd_legacy_run(str(failing), chunk_dir)
