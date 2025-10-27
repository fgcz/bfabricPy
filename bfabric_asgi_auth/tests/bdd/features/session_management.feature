Feature: Session management
  As an authenticated user
  I want my session to be maintained across requests
  So that I don't have to re-authenticate for each request

  Background:
    Given the application is configured with auth middleware
    And I am authenticated with token "valid_test123"

  Scenario: Access protected resource with valid session
    When I request "/"
    Then I should receive a 200 status code
    And the scope should contain "bfabric_session"

  Scenario: Access protected resource without session
    Given I have no session cookie
    When I request "/"
    Then I should receive a 401 status code
    And the response should contain "Not authenticated"

  Scenario: Session persists across multiple requests
    When I request "/" three times
    Then all requests should return 200 status code
