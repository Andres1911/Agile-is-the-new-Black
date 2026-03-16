Feature: Set expenses as recurring

  As a household member
  I want to mark an expense as recurring
  So that the system can automatically create future charges based on a chosen frequency and end condition

  Background:
    Given household "MapleHouse" exists with members
      | member |
      | Alice  |
      | Bob    |
      | Cara   |

  # Normal Flow: Household member creates a recurring expense with an end date
  Scenario: ID018 Household member creates a recurring expense with an end date    (Normal Flow)
    Given the user "Alice" is logged in
    When "Alice" specifies an expense with the following details
      | description | amountCAD |
      | Internet    | 60.00     |
    And "Alice" specifies the expense among the following members
      | payer | shareCAD |
      | Bob   | 20.00    |
      | Cara  | 40.00    |
    And "Alice" marks the expense as recurring
    And "Alice" selects frequency "Monthly"
    And "Alice" selects start date "2026-03-15"
    And "Alice" selects end date "2026-06-15"
    Then the recurring expense is created successfully
    And the system generates the following recurring charges
      | description | amountCAD | date       |
      | Internet    | 60.00     | 2026-03-15 |
      | Internet    | 60.00     | 2026-04-15 |
      | Internet    | 60.00     | 2026-05-15 |
      | Internet    | 60.00     | 2026-06-15 |
    And the expense has "4" sets of the following expense shares
      | user  | amount_owed | paid_amount | is_paid | vote_status |
      | Bob   | 20.00       | 0.00        | False   | PENDING     |
      | Cara  | 40.00       | 0.00        | False   | PENDING     |
    And the message "Recurring expense created successfully" is issued

  # Normal Flow: Household member creates a recurring expense with a fixed number of occurrences
  Scenario: ID018 Household member creates a recurring expense with a fixed number of occurrences    (Alternative Flow)
    Given the user "Alice" is logged in
    When "Alice" specifies an expense with the following details
      | description | amountCAD |
      | Gym         | 25.00     |
    And "Alice" specifies the expense split equally with include_self="false"
    And "Alice" marks the expense as recurring
    And "Alice" selects frequency "Weekly"
    And "Alice" selects start date "2026-03-10"
    And "Alice" selects number of occurrences "4"
    Then the recurring expense is created successfully
    And the system generates the following recurring charges
      | description | amountCAD | date       |
      | Gym         | 25.00     | 2026-03-10 |
      | Gym         | 25.00     | 2026-03-17 |
      | Gym         | 25.00     | 2026-03-24 |
      | Gym         | 25.00     | 2026-03-31 |
    And the expense has "4" sets of the following expense shares
      | user  | amount_owed | paid_amount | is_paid | vote_status |
      | Bob   | 12.50       | 0.00        | False   | PENDING     |
      | Cara  | 12.50       | 0.00        | False   | PENDING     |
    And the message "Recurring expense created successfully" is issued


  # Error Flow: End date before start date
  Scenario: ID018 Household member attempts to create a recurring expense with an end date before the start date    (Error Flow)
    Given the user "Alice" is logged in
    When "Alice" specifies an expense with the following details
      | description | amountCAD |
      | Water       | 40.00     |
    And "Alice" specifies the expense split equally with include_self="false"
    And "Alice" marks the expense as recurring
    And "Alice" selects frequency "Monthly"
    And "Alice" selects start date "2026-06-01"
    And "Alice" selects end date "2026-05-01"
    Then the system rejects the recurring expense creation
    And the system displays error message "End date must be after or equal to the start date"

  # Error Flow: Missing recurrence frequency
  Scenario: ID018 Household member attempts to create a recurring expense without choosing a recurrence frequency    (Error Flow)
    Given the user "Alice" is logged in
    When "Alice" specifies an expense with the following details
      | description | amountCAD |
      | Rent        | 1200.00   |
    And "Alice" specifies the expense split equally with include_self="false"
    And "Alice" marks the expense as recurring
    And "Alice" selects start date "2026-03-01"
    And "Alice" selects end date "2026-06-01"
    Then the system rejects the recurring expense creation
    And the system displays error message "A recurrence frequency must be selected"