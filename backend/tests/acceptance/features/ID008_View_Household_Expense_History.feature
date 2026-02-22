Feature: View household expense history

  As a member of a household
  I want to view the history of all household expenses
  So that I can track our spending over time

  Background:
    Given a user with username "Alice" exists in the system
    And a household named "MapleHouse" exists
    And "Alice" is a member of "MapleHouse"
    And the following expenses exist for "MapleHouse":
      | Description | Amount | PaidBy |
      | Groceries   | 50.00  | Alice  |
      | Internet    | 60.00  | Alice  |
    And the user "Alice" is logged in

  Scenario: Successfully view expense history (Normal Flow)
    When "Alice" requests the expense history for "MapleHouse"
    Then a list of 2 expenses should be returned
    And the first expense should be "Groceries" with amount 50.00
    And the second expense should be "Internet" with amount 60.00

  Scenario: View history for a household with no expenses (Empty State)
    Given a household named "EmptyHome" exists
    And "Alice" is a member of "EmptyHome"
    And "EmptyHome" has no recorded expenses
    When "Alice" requests the expense history for "EmptyHome"
    Then an empty list should be returned
    And the message "No expenses found" is issued

  Scenario: Unauthorized user attempts to view history (Error Flow)
    Given a user with username "Charlie" exists
    And "Charlie" is logged in
    And "Charlie" is not a member of "MapleHouse"
    When "Charlie" requests the expense history for "MapleHouse"
    Then the message "Access denied: Not a household member" is issued
    And no expense data should be returned