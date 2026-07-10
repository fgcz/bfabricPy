from __future__ import annotations


class TransferError(RuntimeError):
    """A file transfer (download or upload) failed.

    Subclasses :class:`RuntimeError` to match bfabricPy's error convention (e.g. the ``use_client``
    CLI decorator catches ``RuntimeError``), so callers integrating this package need not import a
    bespoke base class to handle a failed transfer.
    """
