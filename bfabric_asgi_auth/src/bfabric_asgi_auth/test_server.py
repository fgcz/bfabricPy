import fastapi

from bfabric_asgi_auth.middleware import BfabricAuthMiddleware

app = fastapi.FastAPI()


app.add_middleware(BfabricAuthMiddleware)


# This endpoint prints the request params
@app.get("/debug")
async def debug(request: fastapi.Request):
    bfabric_connection = request.scope.get("bfabric_connection", {})
    return {"bfabric_connection": bfabric_connection}
