import os

import pytest
from bfabric import Bfabric
from bfabric.entities import Workunit
from bfabric_scripts.cli.workunit.diff import (
    DiffRow,
    _resolve_workunit,
    cmd_workunit_diff,
    diff_rows,
)

WORKUNIT_URI = "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=123"
SAMPLE_URI = "https://fgcz-bfabric.uzh.ch/bfabric/sample/show.html?id=5"


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock(spec=Bfabric)
    client.config.base_url = "https://fgcz-bfabric.uzh.ch/bfabric/"
    return client


def _make_param(mocker, context, key, value):
    param = mocker.MagicMock()
    param.get.side_effect = lambda k, d=None: {"context": context}.get(k, d)
    param.key = key
    param.value = value
    return param


def _make_resource(mocker, name, checksum):
    resource = mocker.MagicMock()
    resource.get.side_effect = lambda k, d=None: {"name": name, "filechecksum": checksum}.get(k, d)
    return resource


def _make_workunit(
    mocker,
    *,
    id,
    name,
    status,
    app_id,
    app_name,
    container_class="project",
    container_id=1,
    input_dataset_id=None,
    parameters=(),
    resources=(),
    input_resources=(),
):
    workunit = mocker.MagicMock()
    workunit.id = id
    workunit.get.side_effect = lambda k, d=None: {"name": name, "status": status}.get(k, d)
    workunit.application.id = app_id
    workunit.application.get.side_effect = lambda k, d=None: {"name": app_name}.get(k, d)
    workunit.container.classname = container_class
    workunit.container.id = container_id
    if input_dataset_id is None:
        workunit.input_dataset = None
    else:
        workunit.input_dataset.id = input_dataset_id
    workunit.parameters = [_make_param(mocker, ctx, key, val) for ctx, key, val in parameters]
    workunit.resources = [_make_resource(mocker, n, c) for n, c in resources]
    workunit.input_resources = [_make_resource(mocker, n, c) for n, c in input_resources]
    return workunit


class TestDiffRows:
    def test_equal_values(self):
        rows = diff_rows({"a": "1"}, {"a": "1"})
        assert rows == [DiffRow(key=("a",), left="1", right="1")]
        assert not rows[0].differs

    def test_changed_value(self):
        rows = diff_rows({"a": "1"}, {"a": "2"})
        assert rows[0].differs

    def test_added_and_removed(self):
        rows = diff_rows({"only_left": "1"}, {"only_right": "2"})
        by_key = {row.key: row for row in rows}
        assert by_key[("only_left",)].left == "1"
        assert by_key[("only_left",)].right is None
        assert by_key[("only_right",)].left is None
        assert by_key[("only_left",)].differs
        assert by_key[("only_right",)].differs

    def test_sorted_union_of_keys(self):
        rows = diff_rows({"b": "1", "a": "1"}, {"c": "1"})
        assert [row.key for row in rows] == [("a",), ("b",), ("c",)]

    def test_tuple_keys(self):
        rows = diff_rows({("APPLICATION", "threads"): "4"}, {("APPLICATION", "threads"): "8"})
        assert rows[0].key == ("APPLICATION", "threads")
        assert rows[0].differs


class TestResolveWorkunit:
    def test_resolve_by_uri(self, mock_client, mocker):
        expected = mocker.Mock(spec=Workunit)
        mock_client.reader.read_uri.return_value = expected

        result = _resolve_workunit(WORKUNIT_URI, client=mock_client)

        assert result is expected
        mock_client.reader.read_uri.assert_called_once_with(WORKUNIT_URI, expected_type=Workunit)

    def test_resolve_by_id(self, mock_client, mocker):
        expected = mocker.Mock(spec=Workunit)
        mock_client.reader.read_id.return_value = expected

        result = _resolve_workunit("123", client=mock_client)

        assert result is expected
        mock_client.reader.read_id.assert_called_once_with(Workunit, 123)

    def test_non_workunit_uri_raises(self, mock_client):
        with pytest.raises(ValueError, match="Not a workunit URI"):
            _resolve_workunit(SAMPLE_URI, client=mock_client)

    def test_invalid_reference_raises(self, mock_client):
        with pytest.raises(ValueError, match="Not a workunit URI or numeric ID"):
            _resolve_workunit("not-a-ref", client=mock_client)

    def test_not_found_raises(self, mock_client):
        mock_client.reader.read_id.return_value = None
        with pytest.raises(ValueError, match="Workunit not found"):
            _resolve_workunit("999", client=mock_client)


class TestCmdWorkunitDiff:
    @pytest.fixture(autouse=True)
    def _wide_console(self, mocker):
        # Widen rich's output so table cells aren't wrapped/truncated in captured (non-tty) output.
        mocker.patch.dict(os.environ, {"COLUMNS": "200"})

    def test_renders_fields_and_marks_differences(self, mocker, mock_client, capsys):
        wu1 = _make_workunit(
            mocker,
            id=100,
            name="run",
            status="available",
            app_id=170,
            app_name="MaxQuant",
            parameters=[("APPLICATION", "threads", "4"), ("APPLICATION", "fdr", "0.01")],
            resources=[("out.zip", "aaa")],
        )
        wu2 = _make_workunit(
            mocker,
            id=200,
            name="run",
            status="FAILED",
            app_id=170,
            app_name="MaxQuant",
            parameters=[("APPLICATION", "threads", "8"), ("APPLICATION", "fdr", "0.01")],
            resources=[("out.zip", "aaa"), ("extra.zip", "bbb")],
        )
        mocker.patch("bfabric_scripts.cli.workunit.diff._resolve_workunit", side_effect=[wu1, wu2])

        cmd_workunit_diff("100", "200", client=mock_client)

        out = capsys.readouterr().out
        assert "Workunit diff: WU100 vs WU200" in out
        assert "≠" in out
        assert "FAILED" in out
        assert "threads" in out
        assert "extra.zip" in out

    def test_only_diff_hides_identical_rows(self, mocker, mock_client, capsys):
        wu1 = _make_workunit(
            mocker,
            id=100,
            name="run",
            status="available",
            app_id=170,
            app_name="MaxQuant",
            parameters=[("APPLICATION", "threads", "4"), ("APPLICATION", "fdr", "0.01")],
        )
        wu2 = _make_workunit(
            mocker,
            id=200,
            name="run",
            status="available",
            app_id=170,
            app_name="MaxQuant",
            parameters=[("APPLICATION", "threads", "8"), ("APPLICATION", "fdr", "0.01")],
        )
        mocker.patch("bfabric_scripts.cli.workunit.diff._resolve_workunit", side_effect=[wu1, wu2])

        cmd_workunit_diff("100", "200", client=mock_client, only_diff=True)

        out = capsys.readouterr().out
        # threads differs -> shown; fdr is identical -> hidden; name/status identical -> "(no differences)".
        assert "threads" in out
        assert "fdr" not in out
        assert "(no differences)" in out

    def test_markup_like_values_are_escaped_not_interpreted(self, mocker, mock_client, capsys):
        # rich parses "[/]" as a closing markup tag and raises MarkupError unless the cell is escaped.
        wu1 = _make_workunit(
            mocker,
            id=100,
            name="run",
            status="ok",
            app_id=170,
            app_name="MaxQuant",
            parameters=[("APPLICATION", "expr", "[/]")],
            resources=[("[bold]a.zip", "aaa")],
        )
        wu2 = _make_workunit(
            mocker,
            id=200,
            name="run",
            status="ok",
            app_id=170,
            app_name="MaxQuant",
            parameters=[("APPLICATION", "expr", "value")],
            resources=[],
        )
        mocker.patch("bfabric_scripts.cli.workunit.diff._resolve_workunit", side_effect=[wu1, wu2])

        cmd_workunit_diff("100", "200", client=mock_client)

        out = capsys.readouterr().out
        # No crash, and the literal characters survive rather than being swallowed as markup.
        assert "[/]" in out
        assert "[bold]a.zip" in out


if __name__ == "__main__":
    pytest.main(["-vv", __file__])
