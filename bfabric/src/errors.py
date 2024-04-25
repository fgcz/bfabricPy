from typing import List


class BfabricRequestError(Exception):
    """An error that is returned by the server in response to a full request."""
    def __init__(self, message: str):
        self.message = message

    def __repr__(self):
        return f"RequestError(message={repr(self.message)})"

# TODO: Also test for response-level errors
def get_response_errors(response, endpoint: str) -> List[BfabricRequestError]:
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
