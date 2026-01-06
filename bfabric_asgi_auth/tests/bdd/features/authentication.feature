Feature: Token-based authentication
  As a web application user
  I want to authenticate using a Bfabric token
  So that I can access protected resources

  Background:
    Given the application is configured with auth middleware

  Scenario: Successful authentication with valid token
    When I visit "/landing?token=valid_test123"
    Then I should be redirected to "/"
    And I should have a session cookie
    And the session should contain user information

  Scenario: Authentication fails with invalid token
    When I visit "/landing?token=invalid_token"
    Then I should receive a 400 status code
    And the response should contain "Token validation failed"
    And I should not have a session cookie

  Scenario: Authentication fails without token parameter
    When I visit "/landing"
    Then I should receive a 400 status code
    And the response should contain "Missing token parameter"
