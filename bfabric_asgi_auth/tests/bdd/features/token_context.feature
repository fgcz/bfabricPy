Feature: Token context on BfabricUser
  As an app developer
  I want to access entity_class, entity_id, job_id, and application_id from BfabricUser
  So that I don't need to use the on_success hook to capture token context

  Background:
    Given the application is configured with auth middleware

  Scenario: Token context fields are accessible on BfabricUser
    Given I am authenticated with token "valid_test123"
    When I request the user info endpoint
    Then the scope user entity_class should be "Workunit"
    And the scope user entity_id should be 2
    And the scope user application_id should be 1

  Scenario: Token context round-trips through session
    Given I am authenticated with token "valid_test123"
    When I request the user info endpoint
    Then the scope user should be a BfabricUser
    And the scope user login should be "test123"
    And the scope user entity_class should be "Workunit"
    And the scope user entity_id should be 2
    And the scope user application_id should be 1
