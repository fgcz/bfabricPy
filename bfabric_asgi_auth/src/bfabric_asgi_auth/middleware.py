from asgiref.typing import Scope, ASGIReceiveCallable, ASGISendCallable


class BfabricAuth:
    def __init__(self):
        pass

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        event = await receive()
        await send(
            {
                "bfabric_connection": {
                    "base_url": "https://fgcz-bfabric-test.uzh.ch/bfabric/",
                    "login": "xxx",
                    "webservicepassword": "yyy",
                }
            }
            | event
        )
