import pytest

from bfabric_app_runner.output_registration.register import _check_update_existing_policy
from bfabric_app_runner.specs.outputs_spec import UpdateExisting


@pytest.mark.parametrize(
    ("exists", "policy"),
    [
        (True, UpdateExisting.IF_EXISTS),
        (True, UpdateExisting.REQUIRED),
        (False, UpdateExisting.IF_EXISTS),
        (False, UpdateExisting.NO),
    ],
)
def test_check_update_existing_policy_allows(exists, policy):
    """Combinations the policy permits must not raise."""
    _check_update_existing_policy(exists, policy, description="Entity X")


def test_check_update_existing_policy_no_with_existing_raises():
    with pytest.raises(ValueError, match="already exists"):
        _check_update_existing_policy(True, UpdateExisting.NO, description="Entity X")


def test_check_update_existing_policy_required_with_missing_raises():
    with pytest.raises(ValueError, match="does not exist"):
        _check_update_existing_policy(False, UpdateExisting.REQUIRED, description="Entity X")
