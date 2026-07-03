from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrepareContext:
    """Runtime transport credentials threaded through the prepare pipeline.

    Bundles the credentials needed to stage inputs so that adding a new transport or credential does
    not reopen every ``prepare_*`` signature. Kept deliberately out of the resolved spec: the bearer
    token is a secret and must never be serialized to disk (unlike the non-secret ``FileSourceHttp``).
    """

    ssh_user: str | None = None
    bearer_token: str | None = None
