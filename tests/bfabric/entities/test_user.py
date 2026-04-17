import pytest

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
        (None, False),
    ],
)
def test_is_employee(empdegree, expected, bfabric_instance):
    fields = {} if empdegree is None else {"empdegree": empdegree}
    assert _user(bfabric_instance, **fields).is_employee is expected


def test_is_employee_missing_field(bfabric_instance):
    assert _user(bfabric_instance).is_employee is False
