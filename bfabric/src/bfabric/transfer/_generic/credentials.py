from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel


class Credentials(BaseModel):
    """Transport credentials for a transfer.

    ``token_provider`` supplies the bearer token for authenticated HTTP transfers. It is invoked once
    per request/retry rather than snapshotted, so a caller can hand back a live provider and let the
    token be refreshed underneath -- a long transfer then survives a mid-batch token expiry. ``None``
    means no bearer token is available (a transfer that requires one fails fast). ``ssh_user`` is the
    remote user for the ssh/scp/rsync transports.
    """

    token_provider: Callable[[], str] | None = None
    ssh_user: str | None = None
