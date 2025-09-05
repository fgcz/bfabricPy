Feature: Workflowstep Integration
  Automatic workflowstep creation when workflow_template_step_id is configured in app YAML

  Background:
    Given a bfabric client and workunit definition exist

  Scenario: Workunit fails
    Given app YAML has workflow_template_step_id configured
    And the workflow template step exists
    When workunit execution fails
    Then no workflowstep is created

  Scenario: Workunit succeeds with valid template
    Given app YAML has workflow_template_step_id configured
    And the workflow template step exists
    When workunit execution succeeds
    Then a workflowstep is created and linked to the workunit

  Scenario: Workunit succeeds but template not found
    Given app YAML has workflow_template_step_id configured
    And the workflow template step does not exist
    When workunit execution succeeds
    Then no workflowstep is created
    And an error is logged about misconfigured template
    But workunit remains successful

  Scenario: Workunit succeeds but workflowstep already exists
    Given app YAML has workflow_template_step_id configured
    And the workflow template step exists
    And a workflowstep already exists for this workunit
    When workunit execution succeeds
    Then no duplicate workflowstep is created
    And existing workflowstep is preserved

  Scenario: No workflow template configured
    Given app YAML has no workflow_template_step_id
    When workunit execution succeeds
    Then no workflowstep is created
