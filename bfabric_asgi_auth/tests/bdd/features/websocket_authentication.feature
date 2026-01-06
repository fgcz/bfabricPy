Feature: WebSocket authentication
  As the authentication system
  I want to authenticate WebSocket connections
  So that all connections are secure

  Background:
    Given the application is configured with auth middleware

  Scenario: WebSocket connection without authentication
    Given I have no session cookie
    When I connect to WebSocket "/ws"
    Then the connection should be rejected with code 1008

  Scenario: WebSocket connection with valid session
    Given I am authenticated with token "valid_test123"
    When I connect to WebSocket "/ws"
    Then the connection should be accepted
    And the session should contain "bfabric_session"
