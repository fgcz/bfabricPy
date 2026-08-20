from __future__ import annotations

from typing import Any, cast


class BfabricRequestError(RuntimeError):
    """An error returned by the B-Fabric server in response to a request.

    Typically raised for authentication failures, permission errors, or server-side issues.
    The error is wrapped in a RuntimeError when automatic error checking is enabled.

    :ivar str message: The error message from the B-Fabric server
    """

    def __init__(self, message: str) -> None:
        """Initialize with the error message from the B-Fabric server.

        :param str message: The error message returned by the B-Fabric server
        """
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

    def __hash__(self) -> int:
        return hash(self.message)


class BfabricConfigError(RuntimeError):
    """Raised when the B-Fabric configuration is invalid or cannot be loaded.

    Common causes:
    - Invalid or missing configuration file
    - Missing required credentials
    - Invalid environment name (config_file_env)
    """

    pass


class BfabricInstanceNotConfiguredError(RuntimeError):
    """Raised when token-based authentication is used with an unsupported B-Fabric instance.

    This error occurs during token validation when the instance is not listed in the
    supported_bfabric_instances configuration.
    """

    def __init__(self, instance_name: str) -> None:
        """Initialize with the unsupported B-Fabric instance name.

        :param str instance_name: The URL of the unsupported B-Fabric instance
        """
        super().__init__(f"Instance '{instance_name}' is not configured as supported.")


class BfabricTokenValidationFailedError(RuntimeError):
    """Raised when token validation fails. Base class for the more specific subclasses below.

    Catch this class to handle any validation failure; catch :class:`BfabricTokenExpiredError`
    or :class:`BfabricTokenInvalidError` to react to a specific kind.
    """


class BfabricTokenExpiredError(BfabricTokenValidationFailedError):
    """Raised when token validation fails because the token has expired."""

    def __init__(self, message: str = "Token validation failed: token has expired.") -> None:
        super().__init__(message)


class BfabricTokenInvalidError(BfabricTokenValidationFailedError):
    """Raised when token validation fails because the token is malformed, unknown, or rejected."""

    def __init__(self, message: str = "Token validation failed: token is invalid.") -> None:
        super().__init__(message)


class BfabricOAuthError(RuntimeError):
    """Raised when an OAuth operation fails (token exchange, device code flow, PKCE, etc.)."""


class BfabricUnavailableError(BfabricRequestError):
    """Raised when the B-Fabric instance could not be reached at all.

    Distinct from an error the server *returned*: nothing was refused, the request never landed.
    Callers that only need "this did not work" can keep catching
    :class:`BfabricRequestError`, while a service that wants to retry or degrade can catch this
    specifically.

    It exists because the underlying transports raise types that share no useful base --
    ``suds.transport.TransportError``, ``httpx.ConnectError``, ``urllib.error.URLError`` -- and none
    of them is a ``RuntimeError``, so an unreachable instance would otherwise escape the CLI's error
    handling as a traceback.
    """

    base_url: str

    def __init__(self, base_url: str, cause: BaseException) -> None:
        """
        :param base_url: the instance that could not be reached
        :param cause: the transport-level error, quoted in the message and kept as ``__cause__``
        """
        super().__init__(f"Could not reach the B-Fabric instance at {base_url}: {cause}")
        self.base_url = base_url


def get_response_errors(response: object, endpoint: str) -> list[BfabricRequestError]:
    """
    :param response:  A raw response to a query from an underlying engine
    :param endpoint:  The target endpoint
    :return:          A list of errors for each query result, if that result failed
        Thus, a successful query would result in an empty list
    """
    top_error = cast("str | None", getattr(response, "errorreport", None))
    if top_error:
        return [BfabricRequestError(top_error)]
    if not hasattr(response, endpoint):
        return []
    results = cast("list[object]", getattr(response, endpoint))
    errors: list[BfabricRequestError] = []
    for result in results:
        message = cast("str | None", getattr(result, "errorreport", None))
        if message:
            errors.append(BfabricRequestError(message))
    return errors
