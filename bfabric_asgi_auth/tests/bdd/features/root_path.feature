Feature: Root path handling for mounted apps
  As an application deployed behind a reverse proxy at a sub-path
  I want the middleware to respect scope["root_path"]
  So that landing matches and redirects point to the correct public URL

  Background:
    Given the application is configured with auth middleware

  Scenario: Landing handler matches when proxy forwards full path with root_path set
    When I authenticate with root_path "/myapp" and path "/myapp/landing?token=valid_test123"
    Then the response status should be 303
    And the redirect location should be "/myapp/"

  Scenario: Landing handler matches when proxy strips prefix but root_path is set
    When I authenticate with root_path "/myapp" and path "/landing?token=valid_test123"
    Then the response status should be 303
    And the redirect location should be "/myapp/"

  Scenario: Redirect prepends root_path to custom authenticated_path
    Given the application is configured with authenticated_path "/dashboard"
    When I authenticate with root_path "/myapp" and path "/landing?token=valid_test123"
    Then the response status should be 303
    And the redirect location should be "/myapp/dashboard"

  Scenario: Logout handler matches with root_path in path
    Given I am authenticated with root_path "/myapp" and token "valid_test123"
    When I request with root_path "/myapp" and path "/myapp/logout"
    Then the response status should be 200
