from __future__ import annotations

from pathlib import Path

import pytest

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.transfer.errors import BfabricTransferError, ScopeError
from bfabric.transfer.upload import (
    CreatedResource,
    DuplicateResult,
    UploadRestClient,
    UploadTokenResult,
    api_to_rest_url,
    require_tus,
    tus_sink_for_resource,
)
from bfabric.transfer import FileInfo, TransferSinkTus


def _rest_client(mocker, make_jwt, *, scope: str = "api:read tus containers"):
    client = mocker.MagicMock()
    client.config.base_url = "https://host/bfabric/api/"
    client.auth = mocker.MagicMock(login=OAUTH_LOGIN, password=mocker.MagicMock())
    client.auth.password.get_secret_value.return_value = make_jwt({"scope": scope})
    return UploadRestClient(client)


def _file_info(name: str = "a.txt") -> FileInfo:
    return FileInfo(name=name, md5="abc123", size=42, path=Path(f"/local/{name}"))


def _mock_post(mocker, *, is_success: bool, payload=None, status_code: int = 200, text: str = ""):
    response = mocker.MagicMock(is_success=is_success, status_code=status_code, text=text)
    response.json.return_value = payload
    return mocker.patch("bfabric.transfer.upload.httpx.post", return_value=response)


class TestApiToRestUrl:
    def test_strips_api_suffix_and_trailing_slash(self):
        assert api_to_rest_url("https://host/bfabric/api/") == "https://host/bfabric"

    def test_no_api_suffix_only_strips_trailing_slash(self):
        assert api_to_rest_url("https://host/bfabric/") == "https://host/bfabric"


class TestRequireTus:
    def test_present_is_noop(self):
        # tusclient is a test dependency, so the real mover import succeeds and require_tus returns None.
        assert require_tus() is None

    def test_missing_extra_raises(self, mocker):
        mocker.patch(
            "bfabric.transfer.upload.importlib.import_module",
            side_effect=ImportError("No module named 'tusclient'"),
        )
        with pytest.raises(BfabricTransferError, match="transfer extra"):
            require_tus()


class TestCheckDuplicates:
    def test_maps_response_and_posts_expected_payload(self, mocker, make_jwt):
        payload = [
            {"name": "a.txt", "category": "new", "action": "upload", "existingResourceId": None},
            {"name": "b.txt", "category": "exact_duplicate", "action": "skip", "existingResourceId": 5},
        ]
        mock_post = _mock_post(mocker, is_success=True, payload=payload)
        rest = _rest_client(mocker, make_jwt)

        result = rest.check_duplicates(container_id=4, files=[_file_info("a.txt"), _file_info("b.txt")])

        assert result == [
            DuplicateResult(filename="a.txt", category="new", action="upload", resource_id=None),
            DuplicateResult(filename="b.txt", category="exact_duplicate", action="skip", resource_id=5),
        ]

        mock_post.assert_called_once()
        url = mock_post.call_args.args[0]
        assert url.endswith("/rest/upload/check-duplicates")
        sent = mock_post.call_args.kwargs["json"]
        assert sent["containerId"] == 4
        assert sent["files"] == [
            {"name": "a.txt", "md5": "abc123", "size": 42},
            {"name": "b.txt", "md5": "abc123", "size": 42},
        ]

    def test_failure_raises_transfer_error(self, mocker, make_jwt):
        _mock_post(mocker, is_success=False, status_code=500, text="boom")
        rest = _rest_client(mocker, make_jwt)

        with pytest.raises(BfabricTransferError, match="boom"):
            rest.check_duplicates(container_id=4, files=[_file_info()])


class TestCreateResources:
    def test_maps_response(self, mocker, make_jwt):
        payload = [{"id": 11, "name": "a.txt", "storagePath": "/store/a.txt", "importResourceId": 99}]
        _mock_post(mocker, is_success=True, payload=payload)
        rest = _rest_client(mocker, make_jwt)

        result = rest.create_resources(workunit_id=3, files=[_file_info("a.txt")])

        assert len(result) == 1
        created = result[0]
        assert created.id == 11
        assert created.storage_path == "/store/a.txt"
        assert created.import_resource_id == 99

    def test_failure_raises_transfer_error(self, mocker, make_jwt):
        _mock_post(mocker, is_success=False, status_code=500, text="boom")
        rest = _rest_client(mocker, make_jwt)

        with pytest.raises(BfabricTransferError, match="boom"):
            rest.create_resources(workunit_id=3, files=[_file_info()])


class TestGetUploadToken:
    def test_maps_response(self, mocker, make_jwt):
        payload = {"token": "tok", "tusEndpoint": "https://tus/", "expiresIn": 1800}
        _mock_post(mocker, is_success=True, payload=payload)
        rest = _rest_client(mocker, make_jwt)

        result = rest.get_upload_token(workunit_id=3, resource_ids=[11], import_resource_ids=[99])

        assert result == UploadTokenResult(token="tok", tus_endpoint="https://tus/", expires_in=1800)

    def test_scope_check_runs_before_http(self, mocker, make_jwt):
        mock_post = _mock_post(mocker, is_success=True, payload={})
        rest = _rest_client(mocker, make_jwt, scope="api:read")  # no "tus"

        with pytest.raises(ScopeError):
            rest.get_upload_token(workunit_id=3, resource_ids=[11], import_resource_ids=[99])

        mock_post.assert_not_called()

    def test_failure_raises_transfer_error(self, mocker, make_jwt):
        _mock_post(mocker, is_success=False, status_code=500, text="boom")
        rest = _rest_client(mocker, make_jwt)  # token grants tus, so it reaches the http call

        with pytest.raises(BfabricTransferError, match="boom"):
            rest.get_upload_token(workunit_id=3, resource_ids=[11], import_resource_ids=[99])


class TestTusSinkForResource:
    def test_full_metadata(self):
        resource = CreatedResource(id=11, name="a.txt", storage_path="/store/a.txt", import_resource_id=99)
        token_result = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        sink = tus_sink_for_resource(resource, token_result, workunit_id=3, container_id=4, job_id=7)

        assert sink == TransferSinkTus(
            endpoint="https://tus/",
            token="tok",
            metadata={
                "resourceId": "11",
                "workunitId": "3",
                "containerId": "4",
                "storagePath": "/store/a.txt",
                "importResourceId": "99",
                "jobId": "7",
            },
        )

    def test_no_job_and_no_import_resource(self):
        resource = CreatedResource(id=11, name="a.txt", storage_path="/store/a.txt", import_resource_id=None)
        token_result = UploadTokenResult(token="tok", tus_endpoint="https://tus/")

        sink = tus_sink_for_resource(resource, token_result, workunit_id=3, container_id=4)

        assert sink.metadata == {
            "resourceId": "11",
            "workunitId": "3",
            "containerId": "4",
            "storagePath": "/store/a.txt",
        }
        assert "importResourceId" not in sink.metadata
        assert "jobId" not in sink.metadata
