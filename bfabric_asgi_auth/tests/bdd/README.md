# BDD Tests for bfabric-asgi-auth

This directory contains Behavior-Driven Development (BDD) tests using pytest-bdd.

## Structure

```
tests/bdd/
├── features/              # Gherkin feature files
│   ├── authentication.feature
│   ├── session_management.feature
│   ├── logout.feature
│   ├── middleware_configuration.feature
│   ├── websocket_authentication.feature
│   ├── token_validation.feature
│   └── edge_cases.feature
├── conftest.py           # Fixtures and step definitions
├── test_features.py      # Test runner that loads all features
└── README.md            # This file
```

## Running Tests

```bash
# Run all BDD tests
pytest tests/bdd/

# Run with verbose output
pytest tests/bdd/ -v

# Run specific feature
pytest tests/bdd/ -k authentication

# Run with coverage
pytest tests/bdd/ --cov=src/bfabric_asgi_auth

# Generate HTML report
pytest tests/bdd/ --html=report.html
```

## Writing New Tests

1. Add scenarios to existing `.feature` files in `features/`
2. If needed, add new step definitions to `conftest.py`
3. Tests are automatically discovered by `test_features.py`

## Step Definition Patterns

Common patterns used:

- `Given the application is configured with auth middleware`
- `Given I am authenticated with token "..."`
- `When I visit "..."`
- `When I request "..."`
- `Then I should receive a {status_code} status code`
- `Then the response should contain "..."`
- `Then the scope should contain "..."`
