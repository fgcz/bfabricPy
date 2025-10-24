from asgiref.typing import Scope, ASGIReceiveCallable, ASGISendCallable


class BfabricAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        # Only process HTTP requests
        if scope["type"] == "http":
            # Add auth info to the scope
            scope["bfabric_connection"] = {
                "base_url": "https://fgcz-bfabric-test.uzh.ch/bfabric/",
                "login": "xxx",
                "webservicepassword": "yyy",
            }

        # Pass to the next application
        await self.app(scope, receive, send)
