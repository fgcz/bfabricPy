import fastapi
from starlette.middleware.sessions import SessionMiddleware

from bfabric_asgi_auth.middleware import BfabricAuthMiddleware
from bfabric_asgi_auth.token_validator import create_mock_validator

# Create FastAPI app
app = fastapi.FastAPI()

# Create token validator
token_validator = create_mock_validator()

# IMPORTANT: Middleware order matters!
# add_middleware adds them in REVERSE order, so add BfabricAuthMiddleware FIRST
# so that SessionMiddleware ends up on the OUTSIDE

# Add auth middleware FIRST (so it's inner)
app.add_middleware(
    BfabricAuthMiddleware,
    token_validator=token_validator,
    landing_path="/landing",
    token_param="token",
)

# Add session middleware LAST (so it's outer and wraps BfabricAuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key="test-secret-key-min-32-characters!!",
    max_age=3600,
)


# Protected endpoints


@app.get("/")
async def root(request: fastapi.Request):
    """Root endpoint - shows session info."""
    session_data = request.scope.get("bfabric_session", {})
    return {
        "message": "Welcome to Bfabric authenticated app",
        "bfabric_connection": request.scope.get("bfabric_connection"),
        "user": session_data.get("user_info", {}).get("username"),
    }


@app.get("/debug")
async def debug(request: fastapi.Request):
    """Debug endpoint - shows all request scope data."""
    return {
        "bfabric_session": request.scope.get("bfabric_session"),
        "bfabric_connection": request.scope.get("bfabric_connection"),
        "path": request.scope.get("path"),
    }


@app.get("/user")
async def user_info(request: fastapi.Request):
    """User info endpoint - shows user information from session."""
    session_data = request.scope.get("bfabric_session", {})
    return {
        "user_info": session_data.get("user_info"),
        "client_config": session_data.get("client_config"),
    }
