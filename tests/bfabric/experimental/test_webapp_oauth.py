from __future__ import annotations

from bfabric._oauth.url_token import UrlTokenContext
from bfabric.experimental.webapp_oauth import exchange_launch_token


def test_exchange_launch_token(mocker):
    token_dict = {"access_token": "at-jwt", "refresh_token": "rt"}
    mock_exchange = mocker.patch("bfabric.experimental.webapp_oauth.exchange_token", return_value=token_dict)
    claims = {"sub": "jdoe", "entityId": 5, "entityClassName": "Workunit", "applicationId": 9}
    mock_verify = mocker.patch("bfabric.experimental.webapp_oauth.verify_jwt", return_value=claims)

    result_token, context = exchange_launch_token(
        "https://example.com/bfabric/",
        "launch.jwt",
        client_id="cid",
        client_secret="secret",
    )

    # base_url is normalized (trailing slash stripped) before both calls.
    mock_exchange.assert_called_once_with(
        "https://example.com/bfabric", "launch.jwt", client_id="cid", client_secret="secret"
    )
    mock_verify.assert_called_once_with("https://example.com/bfabric", "at-jwt")
    assert result_token == token_dict
    assert isinstance(context, UrlTokenContext)
    assert context.subject == "jdoe"
    assert context.entity_id == 5
    assert context.entity_class_name == "Workunit"
    assert context.application_id == 9
