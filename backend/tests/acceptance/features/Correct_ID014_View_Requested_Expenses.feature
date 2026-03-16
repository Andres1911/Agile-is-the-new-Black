Feature: View requested expenses

  As a household member
  I want to view expense shares awaiting my approval
  So that I know which expenses I still need to accept or decline

  Background:
    Given a user with username "Alice" exists in the system
    And a user with username "Bob" exists in the system
    And a household named "MapleHouse" exists in the system
    And "Alice" is a member of "MapleHouse"
    And "Bob" is a member of "MapleHouse"
    And the following requested expense shares exist for "MapleHouse"
      | ExpenseDescription | Payee | Payer | AmountOwed | VoteStatus |
      | Groceries          | Alice | Bob   | 20.00      | PENDING    |
    And the user "Bob" is logged in

  Scenario: ID014 Household member views pending requested expenses    (Normal Flow)
    When "Bob" requests to view his requested expenses
    Then a list of 1 requested expenses should be returned
    And the first requested expense should be "Groceries" with amount 20.00
    And the requested expense should show creator "Alice"
    And all returned requested expenses should have vote status "PENDING"

  Scenario: ID014 Household member with no pending requests sees an empty list    (Alternative Flow)
    Given all requested expense shares for "Bob" in "MapleHouse" are accepted
    When "Bob" requests to view his requested expenses
    Then an empty list of requested expenses should be returned

  Scenario: ID014 User not in any household attempts to view requested expenses    (Error Flow)
    Given a user with username "Charlie" exists in the system
    And "Charlie" is not a member of any household
    And "Charlie" is logged in
    When "Charlie" requests to view his requested expenses
    Then the message "Cannot view requested expenses: You are not a member of any household" is issued
    And no requested expense data should be returned