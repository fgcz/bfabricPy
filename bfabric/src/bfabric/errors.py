from __future__ import annotations

from typing import Any


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
