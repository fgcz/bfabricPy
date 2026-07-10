from __future__ import annotations


class BfabricTransferError(RuntimeError):
    """Base class for errors raised by the core B-Fabric transfer binding.

    Subclasses :class:`RuntimeError` to match bfabricPy's error convention (the ``use_client`` CLI
    decorator catches ``RuntimeError``). The actual byte-moving failures are raised as
    ``bfabric.transfer.TransferError`` (also a ``RuntimeError``) by the generic mover layer.
    """


class ScopeError(BfabricTransferError):
    """The OAuth access token provably lacks a scope required for the requested operation.

    Raised by the fail-fast scope pre-check (see :mod:`bfabric.transfer.tokens`). It is a UX aid:
    the server is the real authority on scope, so this only fires when the token decodes cleanly and
    the required scope is definitively absent.
    """


class DuplicateCheckError(BfabricTransferError):
    """The ``/rest/upload/check-duplicates`` call failed."""


class ResourceCreationError(BfabricTransferError):
    """The ``/rest/upload/create-resources`` call failed (or returned unpairable resources)."""


class UploadInitiationError(BfabricTransferError):
    """The ``/rest/upload/initiate`` call (minting the tus upload token) failed."""
