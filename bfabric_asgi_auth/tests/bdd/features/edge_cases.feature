Feature: Edge cases and error handling
  As the authentication system
  I want to handle edge cases gracefully
  So that the application remains secure and stable

  Background:
    Given the application is configured with auth middleware

  Scenario: Token with special characters
    When I visit "/landing?token=valid_token%20with%20spaces"
    Then the token should be URL-decoded correctly
    And I should be redirected to "/"

  Scenario: Session cookie tampering
    Given I am authenticated with token "valid_test123"
    When I modify the session cookie
    And I request "/"
    Then I should receive a 401 status code

  Scenario: Session timeout
    Given the session max_age is 1 second
    And I am authenticated with token "valid_test123"
    When I wait 2 seconds
    And I request "/"
    Then I should receive a 401 status code

  Scenario: Session state validation
    Given I have a session in ERROR state
    When I request "/"
    Then I should receive a 400 status code
    And the response should contain the session error message

  Scenario: Concurrent authentication requests
    When multiple users authenticate with different tokens
    Then each user should have an independent session
    And sessions should not interfere with each other
