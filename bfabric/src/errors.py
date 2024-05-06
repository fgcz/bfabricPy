from __future__ import annotations


class BfabricRequestError(Exception):
    """An error that is returned by the server in response to a full request."""

    def __init__(self, message: str) -> None:
        self.message = message

    def __repr__(self) -> str:
        return f"RequestError(message={repr(self.message)})"


class BfabricConfigError(Exception):
    """An error that is raised when the configuration is invalid."""

    def __init__(self, message: str) -> None:
        self.message = message

    def __repr__(self) -> str:
        return f"ConfigError(message={repr(self.message)})"


# TODO: Also test for response-level errors
def get_response_errors(response, endpoint: str) -> list[BfabricRequestError]:
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
