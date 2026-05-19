from __future__ import annotations

import pytest
from logot import Logot, logged
from pydantic import ValidationError

from bfabric.operations.workunit import CreateWorkunitParams, create_workunit


@pytest.fixture
def mock_client(mocker, bfabric_instance):
    client = mocker.MagicMock(name="Bfabric")
    client.config.base_url = bfabric_instance
    return client


def _initial_response(workunit_id: int = 42) -> list[dict]:
    return [{"id": workunit_id, "classname": "workunit", "_entityclass": "workunit"}]


def _complete_response(workunit_id: int = 42) -> list[dict]:
    return [{"id": workunit_id, "classname": "workunit", "status": "available", "_entityclass": "workunit"}]


def _params(**overrides) -> CreateWorkunitParams:
    defaults = dict(
        container_id=100,
        application_id=5,
        workunit_name="WU",
        parameters={"p": "v"},
        resources={"r": "base64"},
        links={"GitHub": "https://example.com"},
    )
    defaults.update(overrides)
    return CreateWorkunitParams(**defaults)


def test_params_requires_at_least_one_data_kind():
    with pytest.raises(ValidationError):
        CreateWorkunitParams(container_id=1, application_id=2, workunit_name="x")


def test_create_workunit_happy_path(mock_client):
    mock_client.save.side_effect = [
        _initial_response(42),
        [{}],  # resources
        [{}],  # parameters
        [{}],  # links
        _complete_response(42),
    ]
    params = _params()

    workunit = create_workunit(mock_client, params, audit_attributes={"WebApp User": "alice"})

    assert workunit.id == 42
    save_calls = mock_client.save.call_args_list
    assert len(save_calls) == 5
    assert save_calls[0].args[0] == "workunit"
    assert save_calls[1].args[0] == "resource"
    assert save_calls[2].args[0] == "parameter"
    assert save_calls[3].args[0] == "link"
    assert save_calls[4].args == ("workunit", {"id": 42, "status": "available"})


def test_create_workunit_audit_attributes_round_trip(mock_client):
    mock_client.save.side_effect = [
        _initial_response(7),
        [{}],
        [{}],
        [{}],
        _complete_response(7),
    ]
    audit = {"WebApp User": "alice", "Source": "proxy"}

    create_workunit(mock_client, _params(), audit_attributes=audit)

    initial_payload = mock_client.save.call_args_list[0].args[1]
    assert initial_payload["customattribute"] == [
        {"name": "WebApp User", "value": "alice"},
        {"name": "Source", "value": "proxy"},
    ]


def test_create_workunit_returned_entity_has_usable_uri(mock_client, bfabric_instance):
    """Returned entity must support `.uri` even without a bound client (regression smoke)."""
    mock_client.save.side_effect = [
        _initial_response(42),
        [{}],
        [{}],
        [{}],
        _complete_response(42),
    ]

    workunit = create_workunit(mock_client, _params())

    assert str(workunit.uri) == f"{bfabric_instance}workunit/show.html?id=42"


def test_create_workunit_returns_metadata_only_entity(mock_client):
    """The returned Workunit must not carry a bound client — see operations_module.md.

    Lazy reference resolution against the (potentially privileged) `client` used
    to perform the write would silently leak its credentials into reads done
    via the returned entity. We guard against the regression by asserting
    `_client is None` on the result.
    """
    mock_client.save.side_effect = [
        _initial_response(7),
        [{}],
        [{}],
        [{}],
        _complete_response(7),
    ]

    workunit = create_workunit(mock_client, _params())

    assert workunit._client is None


def test_create_workunit_audit_attributes_default_empty(mock_client):
    mock_client.save.side_effect = [
        _initial_response(7),
        [{}],
        [{}],
        [{}],
        _complete_response(7),
    ]

    create_workunit(mock_client, _params())

    initial_payload = mock_client.save.call_args_list[0].args[1]
    assert initial_payload["customattribute"] == []


@pytest.mark.parametrize(
    "fail_step, expected_endpoints_before_failure",
    [
        (1, ["workunit", "resource"]),
        (2, ["workunit", "resource", "parameter"]),
        (3, ["workunit", "resource", "parameter", "link"]),
    ],
)
def test_create_workunit_cleanup_on_failure(mock_client, fail_step, expected_endpoints_before_failure):
    boom = RuntimeError("boom")
    responses: list = [_initial_response(99), [{}], [{}], [{}]]
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
