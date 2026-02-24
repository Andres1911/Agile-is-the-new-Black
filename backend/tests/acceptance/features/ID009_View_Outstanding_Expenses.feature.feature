Feature: View outstanding expenses

  As a member of a household
  I want to view my outstanding expenses
  So that I know how much I still owe

  Background:
    Given a user with username "Alice" exists in the system
    And a household named "MapleHouse" exists in the system
    And "Alice" is a member of "MapleHouse"
    And the following expenses exist for "MapleHouse"
      | Description | Amount | PaidBy | OwedBy |
      | Groceries   | 50.00  | Bob    | Alice  |
      | Internet    | 60.00  | Alice  | Bob    |
      | Utilities   | 100.00 | Bob    | Alice  |
    And the user "Alice" is logged in

  Scenario: Successfully view outstanding expenses (Normal Flow)
    When "Alice" requests her outstanding expenses for "MapleHouse"
    Then a list of 2 outstanding expenses should be returned
    And the first expense should be "Groceries" with amount 50.00
    And the second expense should be "Utilities" with amount 100.00
    And the total outstanding amount should be 150.00

  Scenario: User has no outstanding expenses (Empty State)
    Given all expenses owed by "Alice" are marked as paid
    When "Alice" requests her outstanding expenses for "MapleHouse"
    Then an empty list should be returned
    And the message "No outstanding expenses" is issued

  Scenario: Unauthorized user attempts to view outstanding expenses (Error Flow)
    Given a user with username "Charlie" exists in the system
    And "Charlie" is logged in
    And "Charlie" is not a member of "MapleHouse"
    When "Charlie" requests outstanding expenses for "MapleHouse"
    Then the message "Access denied: You are not a member of this household" is issued
    And no outstanding expense data should be returned