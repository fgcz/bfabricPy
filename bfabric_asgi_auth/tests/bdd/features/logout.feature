Feature: User logout
  As an authenticated user
  I want to be able to log out
  So that my session is terminated

  Background:
    Given the application is configured with auth middleware

  Scenario: Logout when not authenticated
    Given I have no session cookie
    When I request "/logout"
    Then I should receive a 400 status code
    And the response should contain "User not logged in"

  Scenario: Successful logout
    Given I am authenticated with token "valid_test123"
    When I request "/logout"
    Then I should receive a 200 status code
    And the response should contain "Logged out successfully"

  Scenario: Access after logout fails
    Given I am authenticated with token "valid_test123"
    When I request "/logout"
    And I request "/"
    Then I should receive a 401 status code

  Scenario: Re-authentication after logout
    Given I am authenticated with token "valid_test123"
    When I request "/logout"
    And I visit "/landing?token=valid_test456"
    And I request "/"
    Then I should receive a 200 status code
