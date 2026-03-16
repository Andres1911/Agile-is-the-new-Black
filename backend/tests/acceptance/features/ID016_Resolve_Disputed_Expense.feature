Feature: Resolve Disputed Expense
  As a household admin
  I want to settle expenses that have been disputed by a majority of members
  So that I can finalize the household's financial records when members cannot agree

  Background:
    Given household "MapleHouse" exists with members
      | member | role   |
      | Alice  | ADMIN  |
      | Bob    | MEMBER |
      | Cara   | MEMBER |
      | Paul   | MEMBER |
    And user "Alice" has an existing expense with the following details
      | description  | amount | status   |
      | Internet Bill| 60.00  | DISPUTED |
    And the expense has the following expense shares
      | payer | amount_owed | vote_status |
      | Bob   | 20.00       | REJECTED    |
      | Cara  | 20.00       | REJECTED    |
      | Paul  | 20.00       | ACCEPTED    |

  Scenario: ID016 Admin validates a disputed expense    (Normal Flow)
    Given "Alice" is logged in
    When "Alice" marks the disputed expense "Internet Bill" as "VALID"
    Then the system updates the status of "Internet Bill" to "PENDING"
    And the vote status for all payers is forced to "ACCEPTED"
    And the system displays success message "Expense validated by admin"

  Scenario: ID016 Admin invalidates a disputed expense    (Normal Flow)
    Given "Alice" is logged in
    When "Alice" marks the disputed expense "Internet Bill" as "INVALID"
    Then the system updates the status of "Internet Bill" to "REJECTED"
    And the vote status for all payers is forced to "REJECTED"
    And the system displays success message "Expense dismissed by admin"

  Scenario: ID016 Non-admin attempts to resolve a disputed expense    (Error Flow)
    Given "Bob" is logged in
    When "Bob" attempts to mark the disputed expense "Internet Bill" as "VALID"
    Then the system rejects the action
    And the system displays error message "Access denied: Only admins can resolve disputed expenses"
    And the expense status remains "DISPUTED"

  Scenario: ID016 Admin attempts to resolve an expense that is not disputed    (Error Flow)
    Given "Alice" is logged in
    And "Alice" has expense "Utility Bill" with status "ACCEPTED"
    When "Alice" attempts to mark the expense "Utility Bill" as "INVALID"
    Then the system rejects the action
    And the system displays error message "Cannot resolve: Expense is not in a disputed state"