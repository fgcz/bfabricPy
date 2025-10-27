"""BDD tests for bfabric-asgi-auth middleware.

This module discovers and runs all feature files in the features/ directory.
"""

from pytest_bdd import scenarios

# Load all feature files
scenarios("features/authentication.feature")
scenarios("features/session_management.feature")
scenarios("features/logout.feature")
scenarios("features/middleware_configuration.feature")
scenarios("features/websocket_authentication.feature")
scenarios("features/token_validation.feature")
scenarios("features/edge_cases.feature")
