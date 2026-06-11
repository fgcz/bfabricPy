Feature: User scope population
  As a framework author
  I want scope["user"] to be set automatically on authenticated requests
  So that I can access user info via request.user without boilerplate middleware

  Background:
    Given the application is configured with auth middleware

  Scenario: Authenticated request has scope["user"] set as BfabricOAuthUser
    Given I am authenticated with token "valid_test123"
    When I request the user info endpoint
    Then the scope user should be a BfabricOAuthUser
    And the scope user is_authenticated should be true

  Scenario: BfabricOAuthUser properties return correct values
    Given I am authenticated with token "valid_test123"
    When I request the user info endpoint
    Then the scope user display_name should be "test123"
    And the scope user identity should be "test123@https://fgcz-bfabric-test.uzh.ch/bfabric"

  Scenario: subject and base_url properties return correct values
    Given I am authenticated with token "valid_test123"
    When I request the user info endpoint
    Then the scope user subject should be "test123"
    And the scope user base_url should be "https://fgcz-bfabric-test.uzh.ch/bfabric"

  Scenario: Unauthenticated request does not have scope["user"] set
    Given I have no session cookie
    When I visit "/"
    Then I should receive a 401 status code

  Scenario: WebSocket scope gets scope["user"] set
    Given I am authenticated with token "valid_test123"
    When I connect to WebSocket "/ws"
    Then the connection should be accepted
    And the websocket scope user should be set
