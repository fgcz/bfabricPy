"""Binding to B-Fabric's ``/rest/upload/*`` API.

Checks duplicates, creates resource (and import-resource) records, and mints a short-lived tus upload
token -- turning a set of files into a :class:`~bfabric.transfer._generic.sinks.TransferSinkTus` the generic
mover can push to. These are plain-core REST calls over ``httpx`` (no ``tuspy``); only the actual tus
transfer (``bfabric.transfer.send_to_sink``) needs the ``[transfer]`` extra.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, ClassVar, final

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from bfabric.transfer.errors import (
    BfabricTransferError,
    DuplicateCheckError,
    ResourceCreationError,
    UploadInitiationError,
)
from bfabric.transfer.tokens import check_upload_scope, require_oauth
from bfabric.transfer._generic.sinks import TransferSinkTus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bfabric import Bfabric
    from bfabric.transfer._generic.checksums import FileInfo

_TIMEOUT = 60.0


def api_to_rest_url(api_base_url: str) -> str:
    """Derive the B-Fabric REST base URL (``https://host/bfabric``) from the SOAP API base URL."""
    base = api_base_url.rstrip("/")
    if base.endswith("/api"):
        return base[: -len("/api")]
    return base


def require_tus() -> None:
    """Raise :class:`~bfabric.transfer.BfabricTransferError` if the tus mover (the ``[transfer]`` extra) is missing.

    Lets callers fail fast -- before doing irreversible work such as creating a workunit -- instead of
    hitting the missing optional dependency mid-transfer inside :func:`~bfabric.transfer.send_to_sink`.
    Importing the mover module executes its top-level ``import tusclient``, so a missing extra surfaces
    here. The import is done lazily (inside the function) so importing this package never pulls tuspy.
    """
    try:
        _ = importlib.import_module("bfabric.transfer._generic._tus_mover")
    except ImportError as error:
        raise BfabricTransferError(
            "The tus upload mover is not installed; install the transfer extra with "
            "`pip install 'bfabric[transfer]'`."
        ) from error


class DuplicateResult(BaseModel):
    """One entry of the ``check-duplicates`` response."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    filename: str = Field(alias="name")
    category: str  # new | exact_duplicate | renamed_duplicate | content_conflict | batch_duplicate
    action: str  # upload | skip | link
    resource_id: int | None = Field(default=None, alias="existingResourceId")


class CreatedResource(BaseModel):
    """One resource record returned by ``create-resources``."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    id: int
    name: str
    relativepath: str | None = None
    storage_path: str | None = Field(default=None, alias="storagePath")
    import_resource_id: int | None = Field(default=None, alias="importResourceId")


class UploadTokenResult(BaseModel):
    """The ``initiate`` response: the tus endpoint + the short-lived tus upload token."""

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    token: str
    tus_endpoint: str = Field(alias="tusEndpoint")
    expires_in: int = Field(default=3600, alias="expiresIn")


def _file_entries(files: Sequence[FileInfo]) -> list[dict[str, object]]:
    return [{"name": fi.name, "md5": fi.md5, "size": fi.size} for fi in files]


@final
class UploadRestClient:
    """Wraps the ``/rest/upload/*`` endpoints, authenticating with the client's B-Fabric access token."""

    def __init__(self, client: Bfabric) -> None:
        # Refuse a non-OAuth client here so no /rest/upload/* call ever sends a classic web-service
        # password as a bearer token (all REST calls funnel through this client).
        require_oauth(client)
        self._client = client
        self._rest_base_url = api_to_rest_url(str(client.config.base_url))

    @property
    def rest_base_url(self) -> str:
        """The B-Fabric REST base URL (e.g. ``https://host/bfabric``)."""
        return self._rest_base_url

    def _headers(self) -> dict[str, str]:
        # Read the token fresh each call so an OAuth client refreshes it under long batches.
        return {
            "Authorization": f"Bearer {self._client.auth.password.get_secret_value()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def check_duplicates(self, container_id: int, files: Sequence[FileInfo]) -> list[DuplicateResult]:
        """Call ``/rest/upload/check-duplicates`` to classify each file (new / duplicate / conflict)."""
        url = f"{self._rest_base_url}/rest/upload/check-duplicates"
        payload: dict[str, object] = {"containerId": container_id, "files": _file_entries(files)}
        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=_TIMEOUT)
        if not resp.is_success:
            raise DuplicateCheckError(f"check-duplicates REST call failed ({resp.status_code}): {resp.text}")
        return TypeAdapter(list[DuplicateResult]).validate_python(resp.json())

    def create_resources(
        self, workunit_id: int, files: Sequence[FileInfo], *, create_import_resources: bool = True
    ) -> list[CreatedResource]:
        """Call ``/rest/upload/create-resources`` to register resource (and import-resource) records."""
        url = f"{self._rest_base_url}/rest/upload/create-resources"
        payload: dict[str, object] = {
            "workunitId": workunit_id,
            "files": _file_entries(files),
            "createImportResources": create_import_resources,
        }
        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=_TIMEOUT)
        if not resp.is_success:
            raise ResourceCreationError(f"create-resources REST call failed ({resp.status_code}): {resp.text}")
        return TypeAdapter(list[CreatedResource]).validate_python(resp.json())

    def get_upload_token(
        self,
        workunit_id: int,
        resource_ids: Sequence[int],
        import_resource_ids: Sequence[int],
        *,
        job_id: int | None = None,
    ) -> UploadTokenResult:
        """Call ``/rest/upload/initiate`` to mint the tus endpoint + short-lived upload token.

        Runs the fail-fast ``tus`` scope pre-check first: this is the point at which a
        ``TransferSinkTus`` becomes resolvable, so a token missing the scope fails here with a
        re-auth hint rather than as an opaque 401/403 deep in the transfer.
        """
        check_upload_scope(self._client)
        url = f"{self._rest_base_url}/rest/upload/initiate"
        payload: dict[str, object] = {
            "workunitId": workunit_id,
            "resourceIds": list(resource_ids),
            "importResourceIds": list(import_resource_ids),
        }
        if job_id is not None:
            payload["jobId"] = job_id
        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=_TIMEOUT)
        if not resp.is_success:
            raise UploadInitiationError(f"initiate REST call failed ({resp.status_code}): {resp.text}")
        return UploadTokenResult.model_validate(resp.json())


def tus_sink_for_resource(
    resource: CreatedResource,
    token_result: UploadTokenResult,
    *,
    workunit_id: int,
    container_id: int,
    job_id: int | None = None,
) -> TransferSinkTus:
    """Build the :class:`~bfabric.transfer._generic.sinks.TransferSinkTus` for one created resource.

    The ``storagePath`` metadata is taken from the ``create-resources`` record (the storage service
    validates the uploaded path against it, so it must not be composed client-side).
    """
    metadata: dict[str, str] = {
        "resourceId": str(resource.id),
        "workunitId": str(workunit_id),
        "containerId": str(container_id),
        "storagePath": resource.storage_path or "",
    }
    if resource.import_resource_id is not None:
        metadata["importResourceId"] = str(resource.import_resource_id)
    if job_id is not None:
        metadata["jobId"] = str(job_id)
    return TransferSinkTus(endpoint=token_result.tus_endpoint, metadata=metadata, token=token_result.token)
