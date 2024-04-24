class RequestError:
    """An error that is returned by the server in response to a full request."""
    def __init__(self, message: str):
        self.message = message

    def __repr__(self):
        return f"RequestError(message={repr(self.message)})"
