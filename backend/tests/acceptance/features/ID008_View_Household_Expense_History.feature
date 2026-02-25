Feature: View household expense history

  As a member of a household
  I want to view the history of all household expenses
  So that I can track our spending over time

  Background:
    Given a user with username "Alice" exists in the system
    And a household named "MapleHouse" exists in the system
    And "Alice" is a member of "MapleHouse"
    And the following expenses exist for "MapleHouse"
      | Description | Amount | PaidBy |
      | Groceries   | 50.00  | Alice  |
      | Internet    | 60.00  | Alice  |
    And the user "Alice" is logged in

  Scenario: ID008 List all household expenses in chronological order     (Normal Flow)
    When "Alice" requests the expense history for "MapleHouse"
    Then a list of 2 expenses should be returned
    And the first expense should be "Internet" with amount 60.00
    And the second expense should be "Groceries" with amount 50.00

  Scenario: ID008 Handle empty history for a fresh household     (Alternative Flow)
    Given a household named "EmptyHome" exists in the system
    And "Alice" is a member of "EmptyHome"
    And "EmptyHome" has no recorded expenses
    When "Alice" requests the expense history for "EmptyHome"
    Then an empty list should be returned
    And the message "No expenses found" is issued

  Scenario: ID008 Deny expense history access to non-members    (Error Flow)
    Given a user with username "Charlie" exists in the system
    And "Charlie" is logged in
    And "Charlie" is not a member of "MapleHouse"
    When "Charlie" requests the expense history for "MapleHouse"
    Then the message "Access denied: You are not a member of this household" is issued
    And no expense data should be returned