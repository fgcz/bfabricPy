from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class PrepareContext:
    """Runtime transport credentials threaded through the prepare pipeline.

    Bundles the credentials needed to stage inputs so that adding a new transport or credential does
    not reopen every ``prepare_*`` signature. Kept deliberately out of the resolved spec (which is
    serialized to disk): the bearer token is a secret, unlike the non-secret ``FileSourceHttp``.

    ``token_provider`` is a *live* provider -- it is read per request/retry rather than snapshotted,
    so a long multi-file prepare survives a mid-batch OAuth token refresh. It is ``None`` for
    ssh/local-only prepares and for classic login+password clients.
    """

    ssh_user: str | None = None
    token_provider: Callable[[], str] | None = None
