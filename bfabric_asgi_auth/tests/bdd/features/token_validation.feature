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
    Then the token data should contain "user"
    And the token data should contain "entity_class"
    And the token data should contain "entity_id"

  Scenario: Authentication flow populates session with token data
    Given the application is configured with auth middleware
    When I visit "/landing?token=valid_testuser"
    Then I should be redirected to "/"
    And the session should contain "bfabric_session"
    And the session bfabric_session should contain all required fields
    And the hook should have received token data
