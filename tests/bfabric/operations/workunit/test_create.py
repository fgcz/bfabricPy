from __future__ import annotations

import base64
from io import BytesIO

import polars as pl
import pytest
from logot import Logot, logged
from pydantic import ValidationError

from bfabric.operations.workunit import CreateWorkunitParams, WorkunitDataset, create_workunit

DATASET_CSV = b"name,Resource\nalpha,11\nbeta,22\n"


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


@pytest.fixture
def mock_client(mocker, bfabric_instance):
    client = mocker.MagicMock(name="Bfabric")
    client.config.base_url = bfabric_instance
    return client


def _initial_response(workunit_id: int = 42) -> list[dict]:
    return [{"id": workunit_id, "classname": "workunit", "_entityclass": "workunit"}]


def _complete_response(workunit_id: int = 42) -> list[dict]:
    return [{"id": workunit_id, "classname": "workunit", "status": "available", "_entityclass": "workunit"}]


def _arm_happy_path(mock_client, workunit_id: int = 42) -> None:
    mock_client.save.side_effect = [
        _initial_response(workunit_id),
        [{}],  # resources
        [{}],  # parameters
        [{}],  # links
        [{}],  # dataset
        [{}],  # executables
        _complete_response(workunit_id),
    ]


def _params(**overrides) -> CreateWorkunitParams:
    defaults = dict(
        container_id=100,
        application_id=5,
        workunit_name="WU",
        parameters={"p": "v"},
        resources={"r": "base64"},
        links={"GitHub": "https://example.com"},
        dataset=WorkunitDataset(name="results", base64=_b64(DATASET_CSV)),
        executables={"generate.py": "c2NyaXB0"},
    )
    defaults.update(overrides)
    return CreateWorkunitParams(**defaults)


def test_params_requires_at_least_one_data_kind():
    with pytest.raises(ValidationError):
        CreateWorkunitParams(container_id=1, application_id=2, workunit_name="x")


def test_create_workunit_happy_path(mock_client):
    _arm_happy_path(mock_client, workunit_id=42)
    params = _params()

    workunit = create_workunit(mock_client, params, audit_attributes={"WebApp User": "alice"})

    assert workunit.id == 42
    save_calls = mock_client.save.call_args_list
    assert len(save_calls) == 7
    assert save_calls[0].args[0] == "workunit"
    assert save_calls[1].args[0] == "resource"
    assert save_calls[2].args[0] == "parameter"
    assert save_calls[3].args[0] == "link"
    assert save_calls[4].args[0] == "dataset"
    assert save_calls[5].args[0] == "executable"
    assert save_calls[6].args == ("workunit", {"id": 42, "status": "available"})


def test_create_workunit_save_payloads(mock_client):
    _arm_happy_path(mock_client, workunit_id=42)

    create_workunit(mock_client, _params())

    save_calls = mock_client.save.call_args_list
    assert save_calls[0].args == (
        "workunit",
        {
            "containerid": 100,
            "applicationid": 5,
            "name": "WU",
            "description": "",
            "status": "processing",
            "customattribute": [],
            "inputresourceid": [],
        },
    )
    assert save_calls[1].args == (
        "resource",
        [{"base64": "base64", "name": "r", "workunitid": 42}],
    )
    assert save_calls[2].args == (
        "parameter",
        [{"key": "p", "label": "p", "value": "v", "context": "workunit", "workunitid": 42}],
    )
    assert save_calls[3].args == (
        "link",
        [{"parentclassname": "workunit", "parentid": 42, "name": "GitHub", "url": "https://example.com"}],
    )
    assert save_calls[4].args == (
        "dataset",
        {
            "attribute": [
                {"name": "name", "position": 1, "type": "String"},
                {"name": "Resource", "position": 2, "type": "Resource"},
            ],
            "item": [
                {
                    "field": [{"attributeposition": 1, "value": "alpha"}, {"attributeposition": 2, "value": 11}],
                    "position": 1,
                },
                {
                    "field": [{"attributeposition": 1, "value": "beta"}, {"attributeposition": 2, "value": 22}],
                    "position": 2,
                },
            ],
            "name": "results",
            "containerid": 100,
            "workunitid": 42,
        },
    )
    assert save_calls[5].args == (
        "executable",
        [{"name": "generate.py", "context": "WORKUNIT", "workunitid": 42, "base64": "c2NyaXB0"}],
    )


def test_create_workunit_audit_attributes_round_trip(mock_client):
    _arm_happy_path(mock_client, workunit_id=7)
    audit = {"WebApp User": "alice", "Source": "proxy"}

    create_workunit(mock_client, _params(), audit_attributes=audit)

    initial_payload = mock_client.save.call_args_list[0].args[1]
    assert initial_payload["customattribute"] == [
        {"name": "WebApp User", "value": "alice"},
        {"name": "Source", "value": "proxy"},
    ]


def test_create_workunit_returned_entity_has_usable_uri(mock_client, bfabric_instance):
    """Returned entity must support `.uri` even without a bound client (regression smoke)."""
    _arm_happy_path(mock_client, workunit_id=42)

    workunit = create_workunit(mock_client, _params())

    assert str(workunit.uri) == f"{bfabric_instance}/workunit/show.html?id=42"


def test_create_workunit_returns_metadata_only_entity(mock_client):
    """The returned Workunit must not carry a bound client — see operations_module.md.

    Lazy reference resolution against the (potentially privileged) `client` used
    to perform the write would silently leak its credentials into reads done
    via the returned entity. We guard against the regression by asserting
    `_client is None` on the result.
    """
    _arm_happy_path(mock_client, workunit_id=7)

    workunit = create_workunit(mock_client, _params())

    assert workunit._client is None


def test_create_workunit_audit_attributes_default_empty(mock_client):
    _arm_happy_path(mock_client, workunit_id=7)

    create_workunit(mock_client, _params())

    initial_payload = mock_client.save.call_args_list[0].args[1]
    assert initial_payload["customattribute"] == []


@pytest.mark.parametrize(
    "fail_step, expected_endpoints_before_failure",
    [
        (1, ["workunit", "resource"]),
        (2, ["workunit", "resource", "parameter"]),
        (3, ["workunit", "resource", "parameter", "link"]),
        (4, ["workunit", "resource", "parameter", "link", "dataset"]),
        (5, ["workunit", "resource", "parameter", "link", "dataset", "executable"]),
    ],
)
def test_create_workunit_cleanup_on_failure(mock_client, fail_step, expected_endpoints_before_failure):
    boom = RuntimeError("boom")
    responses: list = [_initial_response(99), [{}], [{}], [{}], [{}], [{}]]
    responses[fail_step] = boom
    # cleanup save returns something innocuous
    responses.append([{}])
    mock_client.save.side_effect = responses

    with pytest.raises(RuntimeError, match="boom"):
        create_workunit(mock_client, _params(), audit_attributes={"WebApp User": "alice"})

    save_calls = mock_client.save.call_args_list
    endpoints = [call.args[0] for call in save_calls]
    assert endpoints[: len(expected_endpoints_before_failure)] == expected_endpoints_before_failure
    # last call must be the cleanup
    assert save_calls[-1].args == ("workunit", {"id": 99, "status": "failed"})


def test_create_workunit_cleanup_failure_does_not_mask_original(mock_client, logot: Logot):
    mock_client.save.side_effect = [
        _initial_response(11),
        RuntimeError("step failure"),
        RuntimeError("cleanup failure"),
    ]

    with pytest.raises(RuntimeError, match="step failure"):
        create_workunit(mock_client, _params(), audit_attributes={"WebApp User": "alice"})

    logot.assert_logged(logged.error("Failed to mark workunit 11 failed during cleanup: %s"))


class TestDataset:
    """The output dataset created from base64-encoded tabular content."""

    def test_params_accepts_dataset_only(self):
        params = CreateWorkunitParams(
            container_id=1,
            application_id=2,
            workunit_name="x",
            dataset=WorkunitDataset(name="results", base64=_b64(DATASET_CSV)),
        )

        assert params.dataset is not None
        assert params.dataset.format == "csv"

    def test_skips_dataset_save_when_absent(self, mock_client):
        _arm_happy_path(mock_client, workunit_id=42)

        create_workunit(mock_client, _params(dataset=None))

        endpoints = [call.args[0] for call in mock_client.save.call_args_list]
        assert "dataset" not in endpoints

    @pytest.mark.parametrize("dataset_format", ["csv", "tsv", "parquet"])
    def test_all_formats_decode_to_the_same_payload(self, mock_client, dataset_format):
        table = pl.read_csv(BytesIO(DATASET_CSV))
        if dataset_format == "parquet":
            buffer = BytesIO()
            table.write_parquet(buffer)
            raw = buffer.getvalue()
        else:
            raw = table.write_csv(separator="\t" if dataset_format == "tsv" else ",").encode()
        _arm_happy_path(mock_client, workunit_id=42)

        create_workunit(
            mock_client,
            _params(dataset=WorkunitDataset(name="results", base64=_b64(raw), format=dataset_format)),
        )

        payload = mock_client.save.call_args_list[4].args[1]
        assert payload["attribute"] == [
            {"name": "name", "position": 1, "type": "String"},
            {"name": "Resource", "position": 2, "type": "Resource"},
        ]
        assert payload["item"][0]["field"] == [
            {"attributeposition": 1, "value": "alpha"},
            {"attributeposition": 2, "value": 11},
        ]

    def test_late_non_integer_value_does_not_mistype_column(self, mock_client):
        """Guards `infer_schema_length=None`: polars' default 100-row window would read this as Int64."""
        rows = b"".join(f"row{i},{i}\n".encode() for i in range(200))
        raw = b"name,value\n" + rows + b"row200,n/a\n"
        _arm_happy_path(mock_client, workunit_id=42)

        create_workunit(mock_client, _params(dataset=WorkunitDataset(name="results", base64=_b64(raw))))

        payload = mock_client.save.call_args_list[4].args[1]
        assert payload["attribute"][1] == {"name": "value", "position": 2, "type": "String"}


class TestExecutables:
    """`executables` are saved as `context: "WORKUNIT"` executables of the new workunit."""

    def test_params_accepts_executables_only(self):
        params = CreateWorkunitParams(
            container_id=1, application_id=2, workunit_name="x", executables={"s.py": "eA=="}
        )

        assert params.executables == {"s.py": "eA=="}

    def test_skips_executable_save_when_absent(self, mock_client):
        _arm_happy_path(mock_client, workunit_id=42)

        create_workunit(mock_client, _params(executables={}))

        endpoints = [call.args[0] for call in mock_client.save.call_args_list]
        assert "executable" not in endpoints


class TestInputDataset:
    """`input_dataset_id` references an existing dataset as the workunit's input."""

    def test_omitted_from_payload_when_none(self, mock_client):
        _arm_happy_path(mock_client, workunit_id=42)

        create_workunit(mock_client, _params())

        assert "inputdatasetid" not in mock_client.save.call_args_list[0].args[1]

    def test_present_in_payload_when_set(self, mock_client):
        _arm_happy_path(mock_client, workunit_id=42)

        create_workunit(mock_client, _params(input_dataset_id=1234))

        assert mock_client.save.call_args_list[0].args[1]["inputdatasetid"] == 1234

    def test_alone_does_not_satisfy_the_data_check(self):
        """Like `input_resource_ids`, an input reference is not workunit content."""
        with pytest.raises(ValidationError):
            CreateWorkunitParams(container_id=1, application_id=2, workunit_name="x", input_dataset_id=1234)


class TestParamsAsDict:
    """`params` may be a plain dict, validated inside the operation."""

    def test_dict_is_accepted(self, mock_client):
        # only `parameters` is populated, so the step sequence is initial -> parameter -> complete
        mock_client.save.side_effect = [_initial_response(42), [{}], _complete_response(42)]

        workunit = create_workunit(
            mock_client,
            {
                "container_id": 100,
                "application_id": 5,
                "workunit_name": "WU",
                "parameters": {"p": "v"},
            },
        )

        assert workunit.id == 42
        save_calls = mock_client.save.call_args_list
        assert [call.args[0] for call in save_calls] == ["workunit", "parameter", "workunit"]
        assert save_calls[1].args[1] == [
            {"key": "p", "label": "p", "value": "v", "context": "workunit", "workunitid": 42}
        ]

    def test_nested_dataset_dict_is_coerced(self, mock_client):
        mock_client.save.side_effect = [_initial_response(42), [{}], _complete_response(42)]

        create_workunit(
            mock_client,
            {
                "container_id": 100,
                "application_id": 5,
                "workunit_name": "WU",
                "dataset": {"name": "results", "base64": _b64(DATASET_CSV), "format": "csv"},
            },
        )

        save_calls = mock_client.save.call_args_list
        assert [call.args[0] for call in save_calls] == ["workunit", "dataset", "workunit"]
        assert save_calls[1].args[1]["name"] == "results"
        assert save_calls[1].args[1]["attribute"][1] == {"name": "Resource", "position": 2, "type": "Resource"}

    def test_invalid_dict_raises_before_any_write(self, mock_client):
        with pytest.raises(ValidationError):
            create_workunit(mock_client, {"container_id": 100, "application_id": 5, "workunit_name": "WU"})

        assert not mock_client.save.called

    def test_dict_missing_required_field_raises_before_any_write(self, mock_client):
        with pytest.raises(ValidationError):
            create_workunit(mock_client, {"application_id": 5, "workunit_name": "WU", "parameters": {"p": "v"}})

        assert not mock_client.save.called
