from __future__ import annotations

from typing import Any


class BfabricRequestError(RuntimeError):
    """An error that is returned by the server in response to a full request."""

    def __init__(self, message: str) -> None:
        # Call parent class constructor to properly initialize RuntimeError
        super().__init__(message)
        self.message = message

    def __repr__(self) -> str:
        return f"BfabricRequestError(message={repr(self.message)})"

    def __str__(self) -> str:
        return self.message

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BfabricRequestError):
            return False
        return self.message == other.message


class BfabricConfigError(RuntimeError):
    """An error that is raised when the configuration is invalid."""

    pass


# TODO: Also test for response-level errors
def get_response_errors(response: Any, endpoint: str) -> list[BfabricRequestError]:
    """
    :param response:  A raw response to a query from an underlying engine
    :param endpoint:  The target endpoint
    :return:          A list of errors for each query result, if that result failed
        Thus, a successful query would result in an empty list
    """
    if getattr(response, "errorreport", None):
        return [BfabricRequestError(response.errorreport)]
    elif endpoint in response:
        return [BfabricRequestError(r.errorreport) for r in response[endpoint] if getattr(r, "errorreport", None)]
    else:
        return []
