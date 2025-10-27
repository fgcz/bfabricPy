Feature: Token validation
  As the authentication system
  I want to validate tokens asynchronously
  So that authentication is non-blocking

  Scenario: Mock validator accepts valid tokens
    Given I am using the mock validator
    When I validate token "valid_test123"
    Then the validation should succeed
    And the result should contain client configuration
    And the result should contain user information

  Scenario: Mock validator rejects invalid tokens
    Given I am using the mock validator
    When I validate token "invalid_token"
    Then the validation should fail
    And the error should contain "Invalid token"

  Scenario: Token validation extracts required fields
    Given I am using the mock validator
    When I validate token "valid_test123"
    Then the client config should contain "base_url"
    And the client config should contain "login"
    And the client config should contain "password"
    And the user info should contain "username"
    And the user info should contain "entity_class"
    And the user info should contain "entity_id"
