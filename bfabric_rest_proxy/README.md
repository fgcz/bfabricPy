# bfabric-rest-proxy

REST proxy for B-Fabric web services, with specific functionality for shiny apps.

## Development

To view the API docs, start the server with

```shell
uv run fastapi dev src/bfabric_fastapi_proxy/server.py
```

## Deployment

Deploy with uvicorn or another ASGI server.
Ensure access is controlled, even though we strive to make the proxy as safe as possible, this creates an additional barrier against unauthorized access.
