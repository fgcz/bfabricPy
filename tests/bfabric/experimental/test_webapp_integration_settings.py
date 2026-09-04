from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from bfabric.config.bfabric_auth import BfabricAuth
from bfabric.experimental.webapp_integration_settings import (
    TokenValidationSettings,
    WebappIntegrationSettings,
)

INSTANCE = "https://example.com/bfabric"


@pytest.fixture
def auth() -> BfabricAuth:
    return BfabricAuth(login="feeder", password=SecretStr("x" * 32))


class TestTokenValidationSettings:
    def test_canonicalises_instances(self):
        settings = TokenValidationSettings(
            validation_bfabric_instance=f"{INSTANCE}/",
            supported_bfabric_instances=[f"{INSTANCE}//"],
        )
        assert settings.validation_bfabric_instance == INSTANCE
        assert settings.supported_bfabric_instances == [INSTANCE]

    @pytest.mark.parametrize("validation", [INSTANCE, f"{INSTANCE}/"])
    @pytest.mark.parametrize("supported", [INSTANCE, f"{INSTANCE}/"])
    def test_accepts_either_form_on_both_sides(self, validation, supported):
        settings = TokenValidationSettings(
            validation_bfabric_instance=validation, supported_bfabric_instances=[supported]
        )
        assert settings.validation_bfabric_instance in settings.supported_bfabric_instances

    def test_rejects_an_unsupported_instance(self):
        with pytest.raises(ValidationError, match="must be one of supported_bfabric_instances"):
            TokenValidationSettings(
                validation_bfabric_instance="https://other.example.com/bfabric",
                supported_bfabric_instances=[INSTANCE],
            )

    def test_rejects_a_non_http_instance(self):
        with pytest.raises(ValidationError):
            TokenValidationSettings(validation_bfabric_instance="not-a-url", supported_bfabric_instances=["not-a-url"])


class TestWebappIntegrationSettings:
    def test_canonicalises_feeder_keys(self, auth):
        settings = WebappIntegrationSettings(
            validation_bfabric_instance=INSTANCE,
            supported_bfabric_instances=[f"{INSTANCE}/"],
            feeder_user_credentials={f"{INSTANCE}/": auth},
        )
        assert list(settings.feeder_user_credentials) == [INSTANCE]
        assert settings.feeder_user_credentials[INSTANCE] is auth

    def test_rejects_a_feeder_key_for_an_unsupported_instance(self, auth):
        with pytest.raises(ValidationError, match="only supported bfabric instances"):
            WebappIntegrationSettings(
                validation_bfabric_instance=INSTANCE,
                supported_bfabric_instances=[INSTANCE],
                feeder_user_credentials={"https://other.example.com/bfabric": auth},
            )
