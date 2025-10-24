import fastapi

from bfabric_asgi_auth.middleware import BfabricAuthMiddleware
from bfabric_asgi_auth.session_store import SessionStoreMem
from bfabric_asgi_auth.token_validator import create_mock_validator

# Create FastAPI app
app = fastapi.FastAPI()

# Create session store and token validator
session_store = SessionStoreMem(default_ttl=3600)
token_validator = create_mock_validator()

# Add middleware with configuration
app.add_middleware(
    BfabricAuthMiddleware,
    token_validator=token_validator,
    session_store=session_store,
    landing_path="/landing",
    session_prefix="/session",
    token_param="token",
)


# Protected endpoints (accessed via /session/{id}/...)


@app.get("/")
async def root(request: fastapi.Request):
    """Root endpoint - shows session info."""
    return {
        "message": "Welcome to Bfabric authenticated app",
        "session_id": request.scope.get("session_id"),
        "bfabric_connection": request.scope.get("bfabric_connection"),
    }


@app.get("/debug")
async def debug(request: fastapi.Request):
    """Debug endpoint - shows all request scope data."""
    return {
        "session_id": request.scope.get("session_id"),
        "session_data": request.scope.get("session_data"),
        "bfabric_connection": request.scope.get("bfabric_connection"),
        "path": request.scope.get("path"),
        "original_path": request.url.path,
    }


@app.get("/user")
async def user_info(request: fastapi.Request):
    """User info endpoint - shows user information from session."""
    session_data = request.scope.get("session_data", {})
    return {
        "user_info": session_data.get("user_info"),
        "client_config": session_data.get("client_config"),
    }
