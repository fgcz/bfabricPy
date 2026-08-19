from pathlib import Path

import pytest

from bfabric_app_runner.bfabric_integration.wrapper.wrap_app_yaml_template import WrapAppYamlTemplate


def _render(**overrides: object) -> str:
    params = WrapAppYamlTemplate.Params(
        workunit_id=123,
        app_yaml_path="/path/to/app.yml",
        scratch_root=Path("/scratch"),
        **overrides,
    )
    template = WrapAppYamlTemplate(params=params, path=WrapAppYamlTemplate.default_path())
    return template.render_string()


class TestWrapAppYamlTemplate:
    def test_default_python_version_is_3_13(self):
        """Params defaults the runner's interpreter to the blessed 3.13."""
        assert (
            WrapAppYamlTemplate.Params(
                workunit_id=1, app_yaml_path="/x/app.yml", scratch_root=Path("/scratch")
            ).python_version
            == "3.13"
        )

    def test_runner_launch_is_pinned(self):
        """Regression guard for #494: the runner launch must pin the interpreter.

        Previously `uv run --with "$app_runner_version" bfabric-app-runner` had no `-p`,
        so it floated onto whatever Python uv found (e.g. a prerelease 3.14 where pydantic
        crashed). It must launch via `uv run -p 3.13 --with`.
        """
        script = _render()
        assert 'uv run -p 3.13 --with "$app_runner_version" bfabric-app-runner' in script

    def test_both_uv_run_invocations_are_pinned(self):
        """Neither uv run invocation may float the interpreter.

        The exact count is asserted so the guard fails if an invocation is dropped or an
        unpinned one is reintroduced, not just when an existing line stays pinned.
        """
        script = _render()
        uv_run_lines = [line for line in script.splitlines() if "uv run" in line]
        assert len(uv_run_lines) == 2, f"expected exactly two `uv run` invocations, got {uv_run_lines!r}"
        for line in uv_run_lines:
            assert "-p 3.13" in line, f"unpinned uv run invocation: {line!r}"

    def test_python_version_override_propagates(self):
        """An explicit python_version flows into every uv run invocation."""
        script = _render(python_version="3.12")
        uv_run_lines = [line for line in script.splitlines() if "uv run" in line]
        assert uv_run_lines
        for line in uv_run_lines:
            assert "-p 3.12" in line
        assert "-p 3.13" not in script

    def test_app_yaml_path_stays_quoted(self):
        """Both uses of the path must stay quoted, so a path is never word-split by the shell."""
        script = _render()
        assert 'get_app_runner_version "/path/to/app.yml"' in script
        assert "--app-definition '/path/to/app.yml'" in script


class TestExtractWorkunit:
    @staticmethod
    def _workunit(mocker, program: str):
        workunit = mocker.MagicMock(name="workunit")
        workunit.id = 42
        workunit.application.id = 1000
        workunit.application.executable.__getitem__.side_effect = {"program": program}.__getitem__
        return workunit

    def test_accepts_a_single_path(self, mocker):
        workunit = self._workunit(mocker, "/home/bfabric/slurmworker/config/A375/app.yml")
        params = WrapAppYamlTemplate.Params.extract_workunit(workunit, scratch_root=Path("/scratch"))
        assert params.app_yaml_path == "/home/bfabric/slurmworker/config/A375/app.yml"

    def test_rejects_a_compat_wrapper_program(self, mocker):
        """A two-token program used to render a job script that died on its own first line."""
        program = "/home/bfabric/slurmworker/bin/fgcz_slurm_app_runner_compat.bash /home/bfabric/config/app.yml"
        workunit = self._workunit(mocker, program)
        with pytest.raises(ValueError) as error:
            WrapAppYamlTemplate.Params.extract_workunit(workunit, scratch_root=Path("/scratch"))
        message = str(error.value)
        assert program in message
        assert "workunit 42" in message
        assert "application 1000" in message
