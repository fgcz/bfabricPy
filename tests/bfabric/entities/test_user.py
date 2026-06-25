import pytest

from bfabric._oauth.url_token import UrlTokenContext
from bfabric.entities import User


def _user(bfabric_instance: str, **fields: object) -> User:
    return User(
        data_dict={"classname": "user", "id": 1, "login": "test_user", **fields},
        client=None,
        bfabric_instance=bfabric_instance,
    )


@pytest.mark.parametrize(
    "empdegree, expected",
    [
        ("100", True),
        ("50", True),
        ("0.5", True),
        (100, True),
        (0.5, True),
        ("0", False),
        (0, False),
        ("-10", False),
        ("", False),
        ("not-a-number", False),
    ],
)
def test_is_employee(empdegree, expected, bfabric_instance):
    assert _user(bfabric_instance, empdegree=empdegree).is_employee is expected


def test_is_employee_missing_field_returns_false(bfabric_instance):
    assert _user(bfabric_instance).is_employee is False


def test_is_employee_none_value_returns_false(bfabric_instance):
    assert _user(bfabric_instance, empdegree=None).is_employee is False


def test_current_resolves_subject_via_find_by_login(mocker, bfabric_instance):
    expected = _user(bfabric_instance)
    client = mocker.MagicMock(name="client")
    client.current_identity = UrlTokenContext(subject="jdoe")
    client.reader.query_one.return_value = expected

    result = User.current(client)

    assert result is expected
    client.reader.query_one.assert_called_once_with("user", {"login": "jdoe"}, expected_type=User)


def test_current_returns_none_when_no_subject(mocker, bfabric_instance):
    client = mocker.MagicMock(name="client")
    client.current_identity = UrlTokenContext(subject=None)

    assert User.current(client) is None
    client.reader.query_one.assert_not_called()


def test_current_propagates_identity_error(mocker):
    client = mocker.MagicMock(name="client")
    type(client).current_identity = mocker.PropertyMock(side_effect=ValueError("opaque PAT"))

    with pytest.raises(ValueError, match="opaque PAT"):
        User.current(client)
