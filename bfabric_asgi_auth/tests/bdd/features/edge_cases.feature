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

  Scenario Outline: Session expiration behavior across protocols
    Given the session max_age is 1 second
    And I am authenticated with token "valid_test123"
    When I wait 2 seconds
    And <protocol_action>
    Then <protocol_assertion>

    Examples:
      | protocol_action                | protocol_assertion                    |
      | I request "/"                  | I should receive a 401 status code   |
      | I connect to WebSocket "/ws"   | the connection should be rejected with code 1008 |

  Scenario: Session cookie tampering
    Given I am authenticated with token "valid_test123"
    When I modify the session cookie
    And I request "/"
    Then I should receive a 401 status code

  Scenario: WebSocket connection with tampered session
    Given I am authenticated with token "valid_test123"
    When I modify the session cookie
    And I connect to WebSocket "/ws"
    Then the connection should be rejected with code 1008

  Scenario: Concurrent authentication requests
    When multiple users authenticate with different tokens
    Then each user should have an independent session
    And sessions should not interfere with each other
