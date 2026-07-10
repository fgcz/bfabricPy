"""Tests for the ``bfabric-cli workunit upload`` progress display.

The upload pipeline threads three callbacks out of :func:`bfabric.operations.workunit.upload_files`:
``on_start(total_files, total_bytes)``, ``on_progress(filename, bytes_done, total)`` and
``on_file_done(filename, success)``. These tests cover the CLI's rich renderer (an overall "N/X"
bar plus a per-file bar and a persistent ✓/✗ list) and how it decides whether to render at all.
"""

from __future__ import annotations

from pathlib import Path

import cyclopts
import pytest
from pydantic import ValidationError

from bfabric_scripts.cli.workunit import upload as upload_mod
from bfabric_scripts.cli.workunit.upload import UploadParams


class TestProgressEnabled:
    def test_enabled_when_requested_and_tty(self, mocker):
        mocker.patch.object(upload_mod.sys.stderr, "isatty", return_value=True)
        assert upload_mod._progress_enabled(requested=True) is True

    def test_disabled_when_not_requested(self, mocker):
        mocker.patch.object(upload_mod.sys.stderr, "isatty", return_value=True)
        assert upload_mod._progress_enabled(requested=False) is False

    def test_disabled_when_not_a_tty(self, mocker):
        mocker.patch.object(upload_mod.sys.stderr, "isatty", return_value=False)
        assert upload_mod._progress_enabled(requested=True) is False


class TestUploadProgressReporter:
    def _reporter(self, mocker):
        return upload_mod._UploadProgressReporter(
            live=mocker.MagicMock(),
            overall=mocker.MagicMock(),
            current=mocker.MagicMock(),
        )

    def test_on_start_creates_overall_task_with_total(self, mocker):
        reporter = self._reporter(mocker)
        reporter._overall.add_task.return_value = 1

        reporter.on_start(3, 300)

        reporter._overall.add_task.assert_called_once()
        assert reporter._overall.add_task.call_args.kwargs["total"] == 3

    def test_on_progress_adds_one_task_per_file_and_updates(self, mocker):
        reporter = self._reporter(mocker)
        reporter._current.add_task.side_effect = [10, 20]

        reporter.on_progress("a.raw", 0, 100)
        reporter.on_progress("a.raw", 50, 100)
        reporter.on_progress("b.raw", 30, 60)

        assert reporter._current.add_task.call_count == 2
        reporter._current.update.assert_any_call(10, completed=50, total=100)
        reporter._current.update.assert_any_call(20, completed=30, total=60)

    def test_on_file_done_removes_task_advances_overall_and_prints(self, mocker):
        reporter = self._reporter(mocker)
        reporter._overall.add_task.return_value = 1
        reporter._current.add_task.return_value = 5

        reporter.on_start(2, 0)
        reporter.on_progress("a.raw", 0, 100)
        reporter.on_file_done("a.raw", True)

        reporter._current.remove_task.assert_called_once_with(5)
        reporter._overall.update.assert_called_with(1, completed=1)
        printed = reporter._live.console.print.call_args.args[0]
        assert "1/2" in printed and "a.raw" in printed and "✓" in printed

    def test_on_file_done_failure_prints_cross(self, mocker):
        reporter = self._reporter(mocker)
        reporter._overall.add_task.return_value = 1

        reporter.on_start(1, 0)
        # A file can fail before its first chunk is reported: no current task exists yet.
        reporter.on_file_done("bad.raw", False)

        reporter._current.remove_task.assert_not_called()
        printed = reporter._live.console.print.call_args.args[0]
        assert "✗" in printed and "bad.raw" in printed


class TestUploadProgressContext:
    def test_disabled_yields_none(self):
        with upload_mod._upload_progress(enabled=False) as reporter:
            assert reporter is None

    def test_enabled_yields_reporter(self, mocker):
        mocker.patch.object(upload_mod, "Console")
        mocker.patch.object(upload_mod, "Progress")
        mocker.patch.object(upload_mod, "Group")
        live = mocker.patch.object(upload_mod, "Live")
        live.return_value.__enter__.return_value = mocker.MagicMock()

        with upload_mod._upload_progress(enabled=True) as reporter:
            assert isinstance(reporter, upload_mod._UploadProgressReporter)


class TestUploadParamParsing:
    """The greedy positional ``files`` list must not swallow the container/application ids."""

    def _parse(self, argv: list[str]) -> UploadParams:
        app = cyclopts.App()

        @app.default
        def _run(params: UploadParams): ...

        _cmd, bound, _ = app.parse_args(argv, exit_on_error=False, verbose=False)
        return bound.arguments["params"]

    def test_positional_files_do_not_swallow_container_and_application(self):
        params = self._parse(["a.txt", "b.txt", "--container-id", "403", "--application-id", "419"])
        assert params.files == [Path("a.txt"), Path("b.txt")]
        assert params.container_id == 403
        assert params.application_id == 419

    def test_positional_files_with_workunit_id(self):
        params = self._parse(["a.txt", "--workunit-id", "500"])
        assert params.files == [Path("a.txt")]
        assert params.workunit_id == 500
        assert params.container_id is None


class TestUploadParamsValidation:
    def test_name_and_id_mutually_exclusive(self):
        with pytest.raises(ValidationError, match="mutually exclusive"):
            UploadParams(files=[Path("x")], workunit_id=1, workunit_name="foo")

    def test_requires_container_and_application_without_id(self):
        with pytest.raises(ValidationError, match="required unless"):
            UploadParams(files=[Path("x")])

    def test_workunit_id_alone_is_valid(self):
        params = UploadParams(files=[Path("x")], workunit_id=42)
        assert params.workunit_id == 42

    def test_name_with_container_is_valid(self):
        params = UploadParams(files=[Path("x")], container_id=1, application_id=2, workunit_name="foo")
        assert params.workunit_name == "foo"


class TestCmdWorkunitUpload:
    @pytest.fixture
    def summary(self, mocker):
        return mocker.MagicMock(workunit_id=42, uploaded=1, skipped=0, failed=0, failures=[])

    def _patch_context(self, mocker, reporter):
        context = mocker.MagicMock()
        context.__enter__.return_value = reporter
        context.__exit__.return_value = False
        return mocker.patch.object(upload_mod, "_upload_progress", return_value=context)

    def test_forwards_all_callbacks_when_enabled(self, mocker, summary):
        upload_files = mocker.patch.object(upload_mod, "upload_files", return_value=summary)
        reporter = mocker.MagicMock()
        self._patch_context(mocker, reporter)
        mocker.patch.object(upload_mod, "_progress_enabled", return_value=True)

        params = UploadParams(files=[Path("x")], container_id=1, application_id=2, workunit_name="WU")
        # Call the undecorated function to bypass @use_client's client creation / logging setup.
        upload_mod.cmd_workunit_upload.__wrapped__(params, client=mocker.MagicMock())

        _, kwargs = upload_files.call_args
        assert kwargs["on_progress"] is reporter.on_progress
        assert kwargs["on_start"] is reporter.on_start
        assert kwargs["on_file_done"] is reporter.on_file_done
        assert kwargs["params"].workunit_name == "WU"

    def test_track_job_flows_into_upload_params(self, mocker, summary):
        upload_files = mocker.patch.object(upload_mod, "upload_files", return_value=summary)
        self._patch_context(mocker, None)
        mocker.patch.object(upload_mod, "_progress_enabled", return_value=False)

        params = UploadParams(files=[Path("x")], container_id=1, application_id=2, track_job=True)
        upload_mod.cmd_workunit_upload.__wrapped__(params, client=mocker.MagicMock())

        _, kwargs = upload_files.call_args
        assert kwargs["params"].track_job is True

    def test_none_callbacks_when_disabled(self, mocker, summary):
        upload_files = mocker.patch.object(upload_mod, "upload_files", return_value=summary)
        self._patch_context(mocker, None)
        enabled = mocker.patch.object(upload_mod, "_progress_enabled", return_value=False)

        params = UploadParams(files=[Path("x")], container_id=1, application_id=2, progress=False)
        upload_mod.cmd_workunit_upload.__wrapped__(params, client=mocker.MagicMock())

        enabled.assert_called_once_with(requested=False)
        _, kwargs = upload_files.call_args
        assert kwargs["on_progress"] is None
        assert kwargs["on_start"] is None
        assert kwargs["on_file_done"] is None
