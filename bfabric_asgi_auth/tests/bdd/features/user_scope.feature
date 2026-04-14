Feature: User scope population
  As a framework author
  I want scope["user"] to be set automatically on authenticated requests
  So that I can access user info via request.user without boilerplate middleware

  Background:
    Given the application is configured with auth middleware

  Scenario: Authenticated request has scope["user"] set as BfabricUser
    Given I am authenticated with token "valid_test123"
    When I request the user info endpoint
    Then the scope user should be a BfabricUser
    And the scope user is_authenticated should be true

  Scenario: BfabricUser properties return correct values
    Given I am authenticated with token "valid_test123"
    When I request the user info endpoint
    Then the scope user display_name should be "test123"
    And the scope user identity should be "https://fgcz-bfabric-test.uzh.ch/bfabric/:test123"

  Scenario: session_data property returns the original SessionData
    Given I am authenticated with token "valid_test123"
    When I request the user info endpoint
    Then the scope user session_data should contain the login "test123"

  Scenario: Unauthenticated request does not have scope["user"] set
    Given I have no session cookie
    When I visit "/"
    Then I should receive a 401 status code

  Scenario: WebSocket scope gets scope["user"] set
    Given I am authenticated with token "valid_test123"
    When I connect to WebSocket "/ws"
    Then the connection should be accepted
    And the websocket scope user should be set
