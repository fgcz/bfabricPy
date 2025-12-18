Feature: Middleware configuration
  As a developer
  I want to configure the middleware with custom paths
  So that I can integrate it with my application

  Scenario: Custom landing path
    Given the application is configured with landing_path="/auth/login"
    When I visit "/auth/login?token=valid_test123"
    Then I should be redirected to "/"

  Scenario: Custom token parameter name
    Given the application is configured with token_param="access_token"
    When I visit "/landing?access_token=valid_test123"
    Then I should be redirected to "/"

  Scenario: Custom authenticated redirect path
    Given the application is configured with authenticated_path="/dashboard"
    When I visit "/landing?token=valid_test123"
    Then I should be redirected to "/dashboard"

  Scenario: Custom logout path
    Given the application is configured with logout_path="/signout"
    And I am authenticated with token "valid_test123"
    When I request "/signout"
    Then I should receive a 200 status code
