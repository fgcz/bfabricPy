from __future__ import annotations
from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity

if TYPE_CHECKING:
    from bfabric import Bfabric


class User(Entity):
    ENDPOINT = "user"

    @classmethod
    def find_by_login(cls, login: str, client: Bfabric) -> User | None:
        """Finds a user by their login name."""
        return client.reader.query_one("user", {"login": login}, expected_type=cls)

    @classmethod
    def current(cls, client: Bfabric) -> User | None:
        """Resolves the ``User`` for the client's current (logged-in) identity.

        Resolves the authenticated principal — the token ``subject`` (login) — via
        :attr:`Bfabric.current_identity`. This works across all auth modes
        (password, webapp token, and OAuth: PKCE, device code, client
        credentials). The principal is the *logged-in* user, not the entity an
        application may have been launched from.

        :returns: the matching ``User``, or ``None`` if the identity is known but
            no user record matches it (e.g. an OAuth service account).
        :raises ValueError: if the identity cannot be determined locally, i.e. the
            client authenticates with an opaque Personal Access Token.
        """
        identity = client.current_identity
        if identity.subject:
            return cls.find_by_login(identity.subject, client)
        return None

    @property
    def is_employee(self) -> bool:
        """Whether the user is an employee on the B-Fabric instance (``empdegree`` > 0).

        The ``empdegree`` field is typically only readable with feeder credentials,
        so this property only returns a meaningful answer when the user record was
        fetched with such credentials. If ``empdegree`` is missing or ``None`` (either
        because the field is genuinely unset or because the caller lacks permission
        to read it), this returns ``False``. Callers that need authoritative employee
        status must fetch the user record with feeder credentials.
        """
        empdegree = self.get("empdegree")
        if not isinstance(empdegree, str | int | float) or isinstance(empdegree, bool):
            return False
        try:
            return float(empdegree) > 0
        except ValueError:
            return False
